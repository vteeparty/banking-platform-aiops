#!/usr/bin/env python3
"""
Production-grade Jenkins console log parser for banking platform CI/CD.

Detects and analyzes:
- Maven build failures (compilation, dependencies, tests)
- SonarQube quality gate failures
- Trivy security scan failures
- Kubernetes deployment failures

Outputs structured incident data for further processing.
"""

import re
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class FailureType(Enum):
    """Enumeration of detectable failure types"""
    MAVEN_BUILD = "maven_build"
    SONARQUBE_SCAN = "sonarqube_scan"
    TRIVY_SECURITY = "trivy_security"
    KUBERNETES_DEPLOY = "kubernetes_deploy"
    UNKNOWN = "unknown"


@dataclass
class ParsedFailure:
    """Represents a detected failure in the log"""
    failure_type: FailureType
    line_number: int
    error_line: str
    root_cause: str
    recommended_action: str
    context_lines: List[str]  # Surrounding lines for context
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "failure_type": self.failure_type.value,
            "line_number": self.line_number,
            "error_line": self.error_line,
            "root_cause": self.root_cause,
            "recommended_action": self.recommended_action,
            "context": "\n".join(self.context_lines),
        }


@dataclass
class ParseResult:
    """Complete parse result from a log file"""
    log_file: str
    total_lines: int
    build_status: str  # SUCCESS, FAILURE, ABORTED
    failures: List[ParsedFailure]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "log_file": self.log_file,
            "total_lines": self.total_lines,
            "build_status": self.build_status,
            "failure_count": len(self.failures),
            "failures": [f.to_dict() for f in self.failures],
        }


class JenkinsLogParser:
    """
    Production-grade Jenkins log parser.
    
    Focuses on:
    - Accurate failure detection via regex patterns
    - Root cause analysis with actionable recommendations
    - Minimal false positives
    - Context preservation for debugging
    """
    
    # Maven build failure patterns
    MAVEN_PATTERNS = {
        r"\[ERROR\].*BUILD FAILURE": "Maven build failed",
        r"ERROR.*Failed to execute goal": "Maven goal execution failed",
        r"\[ERROR\].*COMPILATION ERROR": "Java compilation error",
        r"ERROR.*cannot find symbol": "Missing class/method dependency",
        r"Tests run:.*Failures:.*[1-9]": "Unit tests failed",
        r"\[ERROR\].*Dependency.*not found": "Maven dependency missing or inaccessible",
        r"ERROR.*FATAL ERROR": "Fatal Maven error",
        r"\[ERROR\].*ClassNotFoundException": "Class not found at runtime",
        r"\[ERROR\].*NoSuchMethodException": "Method not found (API mismatch)",
    }
    
    # SonarQube failure patterns
    SONARQUBE_PATTERNS = {
        r"Quality Gate.*failed": "Quality gate did not pass",
        r"Quality Gate.*FAILED": "Code quality standards not met",
        r"Coverage.*below.*threshold": "Code coverage below minimum",
        r"Code.*Smell.*threshold": "Too many code smells detected",
        r"SonarQube.*Authentication.*failed": "SonarQube authentication failed",
        r"BLOCKER.*issue.*found": "Blocker level issue detected",
        r"CRITICAL.*issue.*found": "Critical level issue detected",
    }
    
    # Trivy security scan patterns
    TRIVY_PATTERNS = {
        r"CRITICAL.*vulnerability": "Critical security vulnerability found",
        r"CRITICAL.*severity": "Critical security vulnerability found",
        r"HIGH.*severity": "High severity vulnerability detected",
        r"Trivy.*scan.*failed": "Trivy scanning process failed",
        r"image.*pull.*failed": "Failed to pull image for scanning",
        r"Registry.*authentication.*failed": "Cannot authenticate to image registry",
        r"No image provided": "Trivy requires image specification",
        r"Aqua Security Trivy": "Trivy security scan detected",
    }
    
    # Kubernetes deployment failure patterns
    K8S_PATTERNS = {
        r"ImagePullBackOff": "Cannot pull Docker image from registry",
        r"CrashLoopBackOff": "Pod crashing in loop (application error)",
        r"Pending.*0/\d+": "Pod cannot be scheduled on cluster nodes",
        r"kubectl.*error": "Kubernetes API error",
        r"connection refused|refused to connect": "Cannot connect to Kubernetes cluster",
        r"Unauthorized|401": "Kubernetes RBAC authorization failed",
        r"Forbidden|403": "Kubernetes permission denied",
        r"Service.*not.*found": "Kubernetes service does not exist",
        r"Deployment.*failed.*to.*progress": "Deployment stuck or timeout",
        r"Node.*not.*ready": "Kubernetes node is not ready",
    }
    
    # Root cause recommendations
    REMEDIATION_GUIDE = {
        "Maven build failed": "Review Maven error logs, check pom.xml configuration",
        "Java compilation error": "Fix Java syntax errors and import statements",
        "Missing class/method dependency": "Update dependency version or check compatibility",
        "Unit tests failed": "Review test logs, fix failing tests or update test suite",
        "Maven dependency missing or inaccessible": "Verify Maven repository settings, check network connectivity",
        "Class not found at runtime": "Add missing jar to classpath or update dependencies",
        "Method not found (API mismatch)": "Check API compatibility between dependent versions",
        
        "Quality gate did not pass": "Review SonarQube dashboard, address quality issues",
        "Code quality standards not met": "Improve code quality metrics per SonarQube rules",
        "Code coverage below minimum": "Add unit tests to increase coverage percentage",
        "Too many code smells detected": "Refactor code, apply best practices",
        "SonarQube authentication failed": "Verify SonarQube token and server accessibility",
        "Blocker level issue detected": "Fix blocker issues before merging",
        "Critical level issue detected": "Address critical issues immediately",
        
        "Critical security vulnerability found": "Patch vulnerable dependency immediately",
        "High severity vulnerability detected": "Review and patch high-severity vulnerabilities",
        "Trivy scanning process failed": "Check Trivy installation and configuration",
        "Failed to pull image for scanning": "Verify image exists and registry credentials",
        "Cannot authenticate to image registry": "Check registry credentials and permissions",
        "Trivy requires image specification": "Provide image name/tag to Trivy",
        
        "Cannot pull Docker image from registry": "Verify image name, tag, and registry credentials",
        "Pod crashing in loop (application error)": "Check pod logs: kubectl logs <pod> for details",
        "Pod cannot be scheduled on cluster nodes": "Check node resources and pod resource requests",
        "Kubernetes API error": "Check kubectl configuration and cluster connectivity",
        "Cannot connect to Kubernetes cluster": "Verify kubeconfig, cluster URL, and network",
        "Kubernetes RBAC authorization failed": "Check service account permissions and roles",
        "Kubernetes permission denied": "Review RBAC policies and role bindings",
        "Kubernetes service does not exist": "Verify service exists in target namespace",
        "Deployment stuck or timeout": "Check pod logs, resource constraints, or update strategy",
        "Kubernetes node is not ready": "Check node status and investigate node issues",
    }
    
    def __init__(self, log_file_path: str):
        """
        Initialize parser with log file path.
        
        Args:
            log_file_path: Path to Jenkins console log file
        """
        self.log_file_path = Path(log_file_path)
        self.log_lines: List[str] = []
        self.build_status: str = "UNKNOWN"
    
    def parse(self) -> Optional[ParseResult]:
        """
        Parse Jenkins log file and return structured results.
        
        Returns:
            ParseResult with detected failures and build status, or None if file not readable
        """
        if not self._read_log_file():
            return None
        
        self._determine_build_status()
        failures = self._detect_failures()
        
        return ParseResult(
            log_file=str(self.log_file_path),
            total_lines=len(self.log_lines),
            build_status=self.build_status,
            failures=failures,
        )
    
    def _read_log_file(self) -> bool:
        """
        Read log file into memory.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.log_file_path.exists():
                print(f"Error: Log file not found: {self.log_file_path}")
                return False
            
            with open(self.log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                self.log_lines = f.readlines()
            
            return len(self.log_lines) > 0
        except Exception as e:
            print(f"Error reading log file: {e}")
            return False
    
    def _determine_build_status(self) -> None:
        """Determine overall build status from log contents"""
        log_content = "\n".join(self.log_lines).lower()
        
        if re.search(r"build failure|error.*compilation", log_content):
            self.build_status = "FAILURE"
        elif re.search(r"build.*success|finished successfully", log_content):
            self.build_status = "SUCCESS"
        elif re.search(r"build.*aborted|cancelled", log_content):
            self.build_status = "ABORTED"
        else:
            self.build_status = "UNKNOWN"
    
    def _detect_failures(self) -> List[ParsedFailure]:
        """
        Scan log lines for failures and extract details.
        
        Returns:
            List of detected failures with context
        """
        failures: List[ParsedFailure] = []
        
        for idx, line in enumerate(self.log_lines):
            failure_type, pattern_match = self._match_patterns(line)
            
            if failure_type != FailureType.UNKNOWN:
                # Found a failure, extract context and details
                context = self._extract_context(idx, window_size=3)
                root_cause = pattern_match
                action = self.REMEDIATION_GUIDE.get(
                    root_cause, 
                    "Investigate logs for specific error details"
                )
                
                failure = ParsedFailure(
                    failure_type=failure_type,
                    line_number=idx + 1,  # 1-indexed
                    error_line=line.strip(),
                    root_cause=root_cause,
                    recommended_action=action,
                    context_lines=context,
                )
                failures.append(failure)
        
        return failures
    
    def _match_patterns(self, line: str) -> tuple[FailureType, str]:
        """
        Match line against all failure patterns.
        
        Returns:
            Tuple of (FailureType, matched_pattern_description)
        """
        line_lower = line.lower()
        
        # Check Maven patterns
        for pattern, description in self.MAVEN_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                return FailureType.MAVEN_BUILD, description
        
        # Check SonarQube patterns
        for pattern, description in self.SONARQUBE_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                return FailureType.SONARQUBE_SCAN, description
        
        # Check Trivy patterns
        for pattern, description in self.TRIVY_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                return FailureType.TRIVY_SECURITY, description
        
        # Check Kubernetes patterns
        for pattern, description in self.K8S_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                return FailureType.KUBERNETES_DEPLOY, description
        
        return FailureType.UNKNOWN, ""
    
    def _extract_context(self, line_index: int, window_size: int = 3) -> List[str]:
        """
        Extract surrounding lines for context.
        
        Args:
            line_index: Index of the error line
            window_size: Number of lines before/after to include
        
        Returns:
            List of context lines
        """
        start = max(0, line_index - window_size)
        end = min(len(self.log_lines), line_index + window_size + 1)
        
        context = [line.rstrip() for line in self.log_lines[start:end]]
        return context
    
    def extract_build_metrics(self) -> Dict[str, any]:
        """
        Extract useful metrics from build log.
        
        Returns:
            Dictionary with build metrics
        """
        log_content = "\n".join(self.log_lines)
        
        # Extract build duration if available
        duration_match = re.search(
            r"Total time:\s*([\d.]+\s*[smh]+)", 
            log_content, 
            re.IGNORECASE
        )
        build_duration = duration_match.group(1) if duration_match else "Unknown"
        
        # Count total errors and warnings
        error_count = len(re.findall(r"\[ERROR\]|\berror\b", log_content, re.IGNORECASE))
        warning_count = len(re.findall(r"\[WARN\]|\bwarn", log_content, re.IGNORECASE))
        
        # Extract test information if available
        test_match = re.search(
            r"Tests run:\s*(\d+).*Failures:\s*(\d+).*Errors:\s*(\d+)",
            log_content
        )
        tests_info = {
            "total": int(test_match.group(1)),
            "failures": int(test_match.group(2)),
            "errors": int(test_match.group(3)),
        } if test_match else None
        
        return {
            "build_duration": build_duration,
            "error_count": error_count,
            "warning_count": warning_count,
            "tests": tests_info,
        }
