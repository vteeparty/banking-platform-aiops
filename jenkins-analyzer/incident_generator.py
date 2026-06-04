#!/usr/bin/env python3
"""
Incident generation and management for CI/CD pipeline failures.

Takes parsed log data and generates structured incidents with:
- Unique incident IDs
- Severity classification
- Timeline tracking
- Status management
- JSON persistence
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from jenkins_log_parser import FailureType, ParseResult


class SeverityLevel(Enum):
    """Incident severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Incident lifecycle states"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    IGNORED = "ignored"


@dataclass
class Incident:
    """Represents a single incident in the system"""
    incident_id: str
    created_at: str  # ISO 8601 timestamp
    failure_type: str
    severity: str
    status: str
    service: Optional[str]
    title: str
    description: str
    root_cause: str
    recommended_action: str
    error_line: str
    context: str
    build_log: str
    build_status: str
    metrics: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert incident to dictionary for JSON serialization"""
        return asdict(self)


class IncidentGenerator:
    """
    Generates and manages incidents from parsed log data.
    
    Responsibilities:
    - Create incidents from parse results
    - Classify severity
    - Extract service information
    - Persist to JSON storage
    - Query and update incidents
    """
    
    # Severity mapping based on failure type and keywords
    SEVERITY_RULES = {
        FailureType.MAVEN_BUILD: {
            "critical_keywords": ["compilation error", "cannot find symbol", "classnotfound"],
            "high_keywords": ["dependency", "test failure", "build failure"],
            "default": SeverityLevel.HIGH,
        },
        FailureType.SONARQUBE_SCAN: {
            "critical_keywords": ["blocker", "security vulnerability", "authentication failed"],
            "high_keywords": ["quality gate", "coverage", "critical issue"],
            "default": SeverityLevel.MEDIUM,
        },
        FailureType.TRIVY_SECURITY: {
            "critical_keywords": ["critical", "severity"],
            "high_keywords": ["high", "medium"],
            "default": SeverityLevel.HIGH,
        },
        FailureType.KUBERNETES_DEPLOY: {
            "critical_keywords": ["payment", "database", "crash", "unauthorized"],
            "high_keywords": ["deployment failed", "imagepullbackoff", "connection refused"],
            "default": SeverityLevel.HIGH,
        },
    }
    
    # Service name patterns for extraction
    SERVICE_PATTERNS = {
        r"payment[_-]?service": "payment-service",
        r"transaction[_-]?service": "transaction-service",
        r"notification[_-]?service": "notification-service",
        r"auth[_-]?service": "auth-service",
        r"api[_-]?gateway": "api-gateway",
        r"database": "database",
    }
    
    def __init__(self, incidents_file: str = "incidents.json"):
        """
        Initialize incident generator.
        
        Args:
            incidents_file: Path to JSON file for incident storage
        """
        self.incidents_file = Path(incidents_file)
        self.incidents: Dict[str, Incident] = {}
        self._load_incidents()
    
    def _load_incidents(self) -> None:
        """Load existing incidents from JSON file"""
        if self.incidents_file.exists():
            try:
                with open(self.incidents_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for incident_dict in data:
                        incident_id = incident_dict.get("incident_id")
                        if incident_id:
                            self.incidents[incident_id] = Incident(**incident_dict)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Warning: Could not load incidents file: {e}")
                self.incidents = {}
    
    def generate_from_parse_result(self, parse_result: ParseResult) -> List[Incident]:
        """
        Generate incidents from parsed log results.
        
        Args:
            parse_result: Result from JenkinsLogParser.parse()
        
        Returns:
            List of created Incident objects
        """
        created_incidents: List[Incident] = []
        
        for failure in parse_result.failures:
            incident = self._create_incident(failure, parse_result)
            self.incidents[incident.incident_id] = incident
            created_incidents.append(incident)
        
        # Persist to disk
        self.save()
        
        return created_incidents
    
    def _create_incident(self, failure, parse_result: ParseResult) -> Incident:
        """
        Create a single incident from a failure.
        
        Args:
            failure: ParsedFailure from jenkins_log_parser
            parse_result: ParseResult for additional context
        
        Returns:
            Incident object
        """
        incident_id = self._generate_incident_id()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Determine severity
        severity = self._classify_severity(
            failure.failure_type,
            failure.root_cause,
            failure.error_line
        )
        
        # Extract service name if possible
        service = self._extract_service_name(
            failure.error_line,
            failure.context_lines
        )
        
        # Create title based on failure type
        title = self._generate_title(failure.failure_type, service)
        
        # Create description
        description = self._generate_description(
            failure.failure_type,
            failure.error_line,
            service
        )
        
        # Extract metrics
        metrics = {
            "failure_line": failure.line_number,
            "total_lines": parse_result.total_lines,
        }
        
        # Create tags for categorization
        tags = self._generate_tags(failure.failure_type, service)
        
        incident = Incident(
            incident_id=incident_id,
            created_at=timestamp,
            failure_type=failure.failure_type.value,
            severity=severity.value,
            status=IncidentStatus.OPEN.value,
            service=service,
            title=title,
            description=description,
            root_cause=failure.root_cause,
            recommended_action=failure.recommended_action,
            error_line=failure.error_line,
            context="\n".join(failure.context_lines),
            build_log=parse_result.log_file,
            build_status=parse_result.build_status,
            metrics=metrics,
            tags=tags,
        )
        
        return incident
    
    def _generate_incident_id(self) -> str:
        """Generate unique incident ID"""
        unique_part = uuid.uuid4().hex[:8].upper()
        return f"INC-{unique_part}"
    
    def _classify_severity(
        self, 
        failure_type: FailureType, 
        root_cause: str,
        error_line: str
    ) -> SeverityLevel:
        """
        Classify incident severity based on failure type and content.
        
        Args:
            failure_type: Type of failure detected
            root_cause: Root cause description
            error_line: The actual error line
        
        Returns:
            SeverityLevel classification
        """
        combined_text = (root_cause + " " + error_line).lower()
        
        rules = self.SEVERITY_RULES.get(
            failure_type,
            {"critical_keywords": [], "high_keywords": [], "default": SeverityLevel.HIGH}
        )
        
        # Check for critical keywords
        for keyword in rules.get("critical_keywords", []):
            if keyword in combined_text:
                return SeverityLevel.CRITICAL
        
        # Check for high severity keywords
        for keyword in rules.get("high_keywords", []):
            if keyword in combined_text:
                return SeverityLevel.HIGH
        
        # Default severity for this failure type
        return rules.get("default", SeverityLevel.MEDIUM)
    
    def _extract_service_name(self, error_line: str, context_lines: List[str]) -> Optional[str]:
        """
        Extract service name from error line and context.
        
        Args:
            error_line: The error line
            context_lines: Surrounding context lines
        
        Returns:
            Service name if found, None otherwise
        """
        import re
        
        search_text = (error_line + "\n" + "\n".join(context_lines)).lower()
        
        for pattern, service_name in self.SERVICE_PATTERNS.items():
            if re.search(pattern, search_text, re.IGNORECASE):
                return service_name
        
        return None
    
    def _generate_title(self, failure_type: FailureType, service: Optional[str]) -> str:
        """
        Generate human-readable incident title.
        
        Args:
            failure_type: Type of failure
            service: Service name if available
        
        Returns:
            Title string
        """
        service_str = f" in {service}" if service else ""
        
        title_map = {
            FailureType.MAVEN_BUILD: f"Maven build failed{service_str}",
            FailureType.SONARQUBE_SCAN: f"SonarQube scan failed{service_str}",
            FailureType.TRIVY_SECURITY: f"Security vulnerability detected{service_str}",
            FailureType.KUBERNETES_DEPLOY: f"Kubernetes deployment failed{service_str}",
            FailureType.UNKNOWN: "Pipeline error detected",
        }
        
        return title_map.get(failure_type, "Build pipeline failure")
    
    def _generate_description(
        self,
        failure_type: FailureType,
        error_line: str,
        service: Optional[str]
    ) -> str:
        """
        Generate detailed incident description.
        
        Args:
            failure_type: Type of failure
            error_line: The actual error message
            service: Affected service
        
        Returns:
            Description string
        """
        service_info = f"Service: {service}\n" if service else ""
        
        descriptions = {
            FailureType.MAVEN_BUILD: (
                f"{service_info}"
                f"Build failure in Maven compilation step.\n"
                f"Error: {error_line[:100]}"
            ),
            FailureType.SONARQUBE_SCAN: (
                f"{service_info}"
                f"Quality gate or security issue detected by SonarQube.\n"
                f"Error: {error_line[:100]}"
            ),
            FailureType.TRIVY_SECURITY: (
                f"{service_info}"
                f"Security vulnerability found during container scanning.\n"
                f"Error: {error_line[:100]}"
            ),
            FailureType.KUBERNETES_DEPLOY: (
                f"{service_info}"
                f"Kubernetes deployment encountered an error.\n"
                f"Error: {error_line[:100]}"
            ),
            FailureType.UNKNOWN: (
                f"{service_info}"
                f"Build pipeline failed.\n"
                f"Error: {error_line[:100]}"
            ),
        }
        
        return descriptions.get(failure_type, f"Pipeline error: {error_line[:100]}")
    
    def _generate_tags(self, failure_type: FailureType, service: Optional[str]) -> List[str]:
        """
        Generate tags for categorization and search.
        
        Args:
            failure_type: Type of failure
            service: Affected service
        
        Returns:
            List of tags
        """
        tags = [failure_type.value]
        
        if service:
            tags.append(f"service:{service}")
        
        # Add category tags
        if failure_type == FailureType.MAVEN_BUILD:
            tags.extend(["build", "java", "maven"])
        elif failure_type == FailureType.SONARQUBE_SCAN:
            tags.extend(["quality", "security", "scan"])
        elif failure_type == FailureType.TRIVY_SECURITY:
            tags.extend(["security", "vulnerability", "container"])
        elif failure_type == FailureType.KUBERNETES_DEPLOY:
            tags.extend(["deployment", "kubernetes", "infrastructure"])
        
        return tags
    
    def save(self) -> None:
        """
        Persist all incidents to JSON file.
        
        The JSON structure allows for easy import/export and integration
        with other tools.
        """
        incidents_list = [incident.to_dict() for incident in self.incidents.values()]
        
        with open(self.incidents_file, "w", encoding="utf-8") as f:
            json.dump(incidents_list, f, indent=2, ensure_ascii=False)
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """
        Retrieve incident by ID.
        
        Args:
            incident_id: The incident ID
        
        Returns:
            Incident if found, None otherwise
        """
        return self.incidents.get(incident_id)
    
    def update_incident_status(
        self, 
        incident_id: str, 
        status: IncidentStatus,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update incident status and optional resolution notes.
        
        Args:
            incident_id: The incident ID
            status: New IncidentStatus
            notes: Optional resolution notes
        
        Returns:
            True if updated, False if incident not found
        """
        incident = self.incidents.get(incident_id)
        if not incident:
            return False
        
        incident.status = status.value
        incident.updated_at = datetime.utcnow().isoformat() + "Z"
        
        if notes:
            incident.resolution_notes = notes
        
        self.save()
        return True
    
    def get_incidents_by_service(self, service: str) -> List[Incident]:
        """
        Get all incidents for a specific service.
        
        Args:
            service: Service name
        
        Returns:
            List of incidents for that service
        """
        return [
            inc for inc in self.incidents.values()
            if inc.service and service.lower() in inc.service.lower()
        ]
    
    def get_incidents_by_severity(self, severity: SeverityLevel) -> List[Incident]:
        """
        Get all incidents with a specific severity.
        
        Args:
            severity: SeverityLevel
        
        Returns:
            List of incidents with that severity
        """
        return [
            inc for inc in self.incidents.values()
            if inc.severity == severity.value
        ]
    
    def get_open_incidents(self) -> List[Incident]:
        """
        Get all currently open incidents.
        
        Returns:
            List of open incidents
        """
        return [
            inc for inc in self.incidents.values()
            if inc.status == IncidentStatus.OPEN.value
        ]
    
    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics about all incidents.
        
        Returns:
            Dictionary with counts by severity, type, service, etc.
        """
        by_severity = {}
        by_type = {}
        by_service = {}
        by_status = {}
        
        for incident in self.incidents.values():
            # Count by severity
            sev = incident.severity
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            # Count by type
            ftype = incident.failure_type
            by_type[ftype] = by_type.get(ftype, 0) + 1
            
            # Count by service
            if incident.service:
                svc = incident.service
                by_service[svc] = by_service.get(svc, 0) + 1
            
            # Count by status
            status = incident.status
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_incidents": len(self.incidents),
            "by_severity": by_severity,
            "by_failure_type": by_type,
            "by_service": by_service,
            "by_status": by_status,
        }
