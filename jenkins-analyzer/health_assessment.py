#!/usr/bin/env python3
"""
Health assessment module for CI/CD pipeline and deployment systems.

Analyzes:
- Incident trends and patterns
- Service health based on recent failures
- Build success rates
- Deployment readiness assessment

Generates:
- Health scores (0-100)
- Risk levels (Low, Medium, High, Critical)
- Actionable recommendations
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from incident_generator import IncidentGenerator, SeverityLevel, IncidentStatus


class HealthStatus(Enum):
    """Overall health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ServiceHealth:
    """Health metrics for a specific service"""
    service_name: str
    total_incidents: int
    critical_incidents: int
    high_incidents: int
    medium_incidents: int
    open_incidents: int
    incident_trend: str  # increasing, stable, decreasing
    health_score: int  # 0-100
    risk_level: str
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class PipelineHealth:
    """Overall pipeline health assessment"""
    timestamp: str
    health_status: str  # HEALTHY, DEGRADED, UNHEALTHY, CRITICAL
    overall_health_score: int  # 0-100
    overall_risk_level: str
    build_success_rate: float  # 0-100
    mean_time_to_recovery: Optional[str]  # Average time to fix issues
    services: List[ServiceHealth]
    critical_areas: List[str]  # Areas needing immediate attention
    recommendations: List[str]  # Actionable recommendations
    incident_summary: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "health_status": self.health_status,
            "overall_health_score": self.overall_health_score,
            "overall_risk_level": self.overall_risk_level,
            "build_success_rate": self.build_success_rate,
            "mean_time_to_recovery": self.mean_time_to_recovery,
            "services": [s.to_dict() for s in self.services],
            "critical_areas": self.critical_areas,
            "recommendations": self.recommendations,
            "incident_summary": self.incident_summary,
        }


class HealthAssessment:
    """
    Assesses overall health of CI/CD pipeline and deployments.
    
    Combines incident data with trends and patterns to provide
    comprehensive health insights.
    """
    
    def __init__(self, incidents_file: str = "incidents.json"):
        """
        Initialize health assessment.
        
        Args:
            incidents_file: Path to incidents JSON file
        """
        self.incident_gen = IncidentGenerator(incidents_file)
        self.incidents_file = Path(incidents_file)
    
    def assess(self) -> PipelineHealth:
        """
        Perform full health assessment of the pipeline.
        
        Returns:
            PipelineHealth object with complete assessment
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Get all incidents
        all_incidents = list(self.incident_gen.incidents.values())
        
        # Calculate summary statistics
        incident_summary = self.incident_gen.get_summary_stats()
        
        # Assess services
        services_health = self._assess_services()
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(services_health)
        
        # Determine health status
        health_status = self._determine_health_status(overall_score)
        
        # Determine risk level
        risk_level = self._determine_risk_level(all_incidents)
        
        # Calculate build success rate
        success_rate = self._calculate_success_rate()
        
        # Calculate MTTR
        mttr = self._calculate_mean_time_to_recovery()
        
        # Identify critical areas
        critical_areas = self._identify_critical_areas(services_health, all_incidents)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            services_health,
            all_incidents,
            critical_areas
        )
        
        return PipelineHealth(
            timestamp=timestamp,
            health_status=health_status.value,
            overall_health_score=overall_score,
            overall_risk_level=risk_level.value,
            build_success_rate=success_rate,
            mean_time_to_recovery=mttr,
            services=services_health,
            critical_areas=critical_areas,
            recommendations=recommendations,
            incident_summary=incident_summary,
        )
    
    def _assess_services(self) -> List[ServiceHealth]:
        """
        Assess health of each service.
        
        Returns:
            List of ServiceHealth objects for each service
        """
        services_dict: Dict[str, List] = {}
        
        # Group incidents by service
        for incident in self.incident_gen.incidents.values():
            service = incident.service or "Unknown"
            if service not in services_dict:
                services_dict[service] = []
            services_dict[service].append(incident)
        
        services_health: List[ServiceHealth] = []
        
        for service, incidents in services_dict.items():
            # Count incidents by severity
            critical = sum(1 for i in incidents if i.severity == SeverityLevel.CRITICAL.value)
            high = sum(1 for i in incidents if i.severity == SeverityLevel.HIGH.value)
            medium = sum(1 for i in incidents if i.severity == SeverityLevel.MEDIUM.value)
            open_count = sum(1 for i in incidents if i.status == IncidentStatus.OPEN.value)
            
            # Determine trend
            trend = self._analyze_incident_trend(incidents)
            
            # Calculate health score
            score = self._calculate_service_health_score(
                critical, high, medium, len(incidents)
            )
            
            # Determine risk level
            risk = self._determine_service_risk_level(critical, high, medium)
            
            # Generate service-specific recommendations
            service_recs = self._generate_service_recommendations(
                service, incidents, critical, high
            )
            
            services_health.append(ServiceHealth(
                service_name=service,
                total_incidents=len(incidents),
                critical_incidents=critical,
                high_incidents=high,
                medium_incidents=medium,
                open_incidents=open_count,
                incident_trend=trend,
                health_score=score,
                risk_level=risk.value,
                recommendations=service_recs,
            ))
        
        return services_health
    
    def _calculate_overall_score(self, services: List[ServiceHealth]) -> int:
        """
        Calculate overall pipeline health score (0-100).
        
        Weighting:
        - Services with more critical incidents lower the score more
        - Open incidents penalty is higher
        - Closed incidents have minimal impact
        
        Args:
            services: List of service health objects
        
        Returns:
            Overall health score 0-100
        """
        if not services:
            return 100
        
        # Start at 100
        score = 100
        
        for service in services:
            # Penalty for critical incidents: -10 each
            score -= service.critical_incidents * 10
            
            # Penalty for high incidents: -5 each
            score -= service.high_incidents * 5
            
            # Penalty for medium incidents: -2 each
            score -= service.medium_incidents * 2
            
            # Additional penalty if trend is increasing
            if service.incident_trend == "increasing":
                score -= 5
        
        # Ensure score stays in range 0-100
        return max(0, min(100, score))
    
    def _determine_health_status(self, score: int) -> HealthStatus:
        """Determine health status from score"""
        if score >= 80:
            return HealthStatus.HEALTHY
        elif score >= 60:
            return HealthStatus.DEGRADED
        elif score >= 40:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.CRITICAL
    
    def _determine_risk_level(self, incidents: List) -> RiskLevel:
        """
        Determine overall risk level based on incidents.
        
        Args:
            incidents: All incidents
        
        Returns:
            RiskLevel classification
        """
        if not incidents:
            return RiskLevel.LOW
        
        # Count critical/high severity incidents
        critical_count = sum(1 for i in incidents if i.severity == SeverityLevel.CRITICAL.value)
        high_count = sum(1 for i in incidents if i.severity == SeverityLevel.HIGH.value)
        open_count = sum(1 for i in incidents if i.status == IncidentStatus.OPEN.value)
        
        # Risk assessment logic
        if critical_count > 0:
            return RiskLevel.CRITICAL
        elif critical_count + high_count > 5:
            return RiskLevel.HIGH
        elif open_count > 10:
            return RiskLevel.HIGH
        elif high_count > 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _determine_service_risk_level(self, critical: int, high: int, medium: int) -> RiskLevel:
        """Determine risk level for a specific service"""
        if critical > 0:
            return RiskLevel.CRITICAL
        elif critical + high > 3:
            return RiskLevel.HIGH
        elif high > 2 or medium > 5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_service_health_score(
        self,
        critical: int,
        high: int,
        medium: int,
        total: int
    ) -> int:
        """Calculate health score for a service (0-100)"""
        if total == 0:
            return 100
        
        score = 100
        score -= critical * 15
        score -= high * 8
        score -= medium * 3
        
        return max(0, min(100, score))
    
    def _analyze_incident_trend(self, incidents: List) -> str:
        """
        Analyze incident trend over time.
        
        Args:
            incidents: List of incidents
        
        Returns:
            "increasing", "stable", or "decreasing"
        """
        if len(incidents) < 2:
            return "stable"
        
        # Sort by creation time
        sorted_incidents = sorted(
            incidents,
            key=lambda x: x.created_at,
            reverse=True
        )
        
        # Split into recent and older
        now = datetime.utcnow()
        recent = []
        older = []
        
        for incident in sorted_incidents:
            try:
                created = datetime.fromisoformat(incident.created_at.replace("Z", "+00:00"))
                # Convert to naive datetime for comparison
                created_naive = created.replace(tzinfo=None)
                if (now - created_naive).days <= 7:
                    recent.append(incident)
                else:
                    older.append(incident)
            except (ValueError, AttributeError):
                older.append(incident)
        
        if not older or not recent:
            return "stable"
        
        recent_critical = sum(1 for i in recent if i.severity == SeverityLevel.CRITICAL.value)
        older_critical = sum(1 for i in older if i.severity == SeverityLevel.CRITICAL.value)
        
        if recent_critical > older_critical:
            return "increasing"
        elif recent_critical < older_critical:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_success_rate(self) -> float:
        """
        Calculate build success rate based on incidents.
        
        Assumes that services with no incidents have success rate,
        and incidents reduce the rate proportionally.
        
        Returns:
            Success rate as percentage (0-100)
        """
        all_incidents = list(self.incident_gen.incidents.values())
        if not all_incidents:
            return 100.0
        
        # Estimate based on failure types
        failure_types = {}
        for incident in all_incidents:
            ftype = incident.failure_type
            failure_types[ftype] = failure_types.get(ftype, 0) + 1
        
        # More build failures indicate lower success rate
        maven_failures = failure_types.get("maven_build", 0)
        
        # Rough estimate: subtract percentage based on failures
        success_rate = 100.0 - (maven_failures * 5.0)
        
        return max(0.0, min(100.0, success_rate))
    
    def _calculate_mean_time_to_recovery(self) -> Optional[str]:
        """
        Calculate mean time to recovery from resolved incidents.
        
        Returns:
            MTTR as formatted string (e.g., "2h 30m"), or None if insufficient data
        """
        resolved = [
            i for i in self.incident_gen.incidents.values()
            if i.status == IncidentStatus.RESOLVED.value and i.updated_at
        ]
        
        if not resolved:
            return None
        
        total_duration = timedelta(0)
        
        for incident in resolved:
            try:
                created = datetime.fromisoformat(incident.created_at.replace("Z", "+00:00"))
                updated = datetime.fromisoformat(incident.updated_at.replace("Z", "+00:00"))
                total_duration += (updated - created)
            except (ValueError, AttributeError):
                continue
        
        if not resolved:
            return None
        
        avg_duration = total_duration / len(resolved)
        hours = int(avg_duration.total_seconds() // 3600)
        minutes = int((avg_duration.total_seconds() % 3600) // 60)
        
        return f"{hours}h {minutes}m"
    
    def _identify_critical_areas(
        self,
        services: List[ServiceHealth],
        all_incidents: List
    ) -> List[str]:
        """
        Identify areas requiring immediate attention.
        
        Args:
            services: Service health list
            all_incidents: All incidents
        
        Returns:
            List of critical areas
        """
        critical_areas: List[str] = []
        
        # Check for services with critical incidents
        for service in services:
            if service.critical_incidents > 0:
                critical_areas.append(
                    f"Critical incidents in {service.service_name}"
                )
            if service.incident_trend == "increasing":
                critical_areas.append(
                    f"Increasing incident trend in {service.service_name}"
                )
        
        # Check for high volume of open incidents
        open_count = sum(1 for i in all_incidents if i.status == IncidentStatus.OPEN.value)
        if open_count > 10:
            critical_areas.append(
                f"High number of open incidents ({open_count})"
            )
        
        # Check for specific failure types
        failure_types = {}
        for incident in all_incidents:
            ftype = incident.failure_type
            failure_types[ftype] = failure_types.get(ftype, 0) + 1
        
        for ftype, count in failure_types.items():
            if count > 5:
                critical_areas.append(f"High {ftype} failure rate ({count} incidents)")
        
        return critical_areas[:5]  # Return top 5 critical areas
    
    def _generate_recommendations(
        self,
        services: List[ServiceHealth],
        all_incidents: List,
        critical_areas: List[str]
    ) -> List[str]:
        """
        Generate actionable recommendations based on health assessment.
        
        Args:
            services: Service health list
            all_incidents: All incidents
            critical_areas: Identified critical areas
        
        Returns:
            List of recommendations
        """
        recommendations: List[str] = []
        
        # Recommendation for critical areas
        if critical_areas:
            recommendations.append(
                f"Address critical areas immediately: {critical_areas[0]}"
            )
        
        # Recommendations per service
        for service in services:
            if service.critical_incidents > 0:
                recommendations.append(
                    f"Investigate and resolve critical incidents in {service.service_name}"
                )
            
            if service.incident_trend == "increasing":
                recommendations.append(
                    f"Review recent changes in {service.service_name} to identify root causes"
                )
            
            if service.recommendations:
                recommendations.extend(service.recommendations[:2])
        
        # General recommendations
        open_incidents = sum(
            1 for i in all_incidents 
            if i.status == IncidentStatus.OPEN.value
        )
        if open_incidents > 5:
            recommendations.append(
                f"Triage and assign {open_incidents} open incidents for resolution"
            )
        
        return recommendations[:10]  # Return top 10 recommendations
    
    def _generate_service_recommendations(
        self,
        service: str,
        incidents: List,
        critical: int,
        high: int
    ) -> List[str]:
        """Generate recommendations for a specific service"""
        recs: List[str] = []
        
        if critical > 0:
            recs.append(f"Resolve {critical} critical incidents in {service} urgently")
        
        if high > 0:
            recs.append(f"Address {high} high-severity issues in {service}")
        
        # Identify common failure types
        failure_types = {}
        for incident in incidents:
            ftype = incident.failure_type
            failure_types[ftype] = failure_types.get(ftype, 0) + 1
        
        for ftype, count in sorted(failure_types.items(), key=lambda x: x[1], reverse=True):
            if count > 2:
                recs.append(f"Investigate pattern: {count} {ftype} failures in {service}")
        
        return recs
    
    def save_assessment(self, output_file: str = "health_assessment.json") -> None:
        """
        Save health assessment to JSON file.
        
        Args:
            output_file: Path to output JSON file
        """
        assessment = self.assess()
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(assessment.to_dict(), f, indent=2, ensure_ascii=False)
    
    def generate_report(self) -> str:
        """
        Generate human-readable health report.
        
        Returns:
            Formatted report string
        """
        assessment = self.assess()
        
        report = []
        report.append("=" * 70)
        report.append("CI/CD PIPELINE HEALTH ASSESSMENT REPORT")
        report.append("=" * 70)
        report.append("")
        
        # Overall status
        report.append("OVERALL STATUS")
        report.append("-" * 70)
        report.append(f"Health Status: {assessment.health_status.upper()}")
        report.append(f"Health Score: {assessment.overall_health_score}/100")
        report.append(f"Risk Level: {assessment.overall_risk_level.upper()}")
        report.append(f"Build Success Rate: {assessment.build_success_rate:.1f}%")
        if assessment.mean_time_to_recovery:
            report.append(f"Mean Time to Recovery: {assessment.mean_time_to_recovery}")
        report.append("")
        
        # Incident summary
        report.append("INCIDENT SUMMARY")
        report.append("-" * 70)
        summary = assessment.incident_summary
        report.append(f"Total Incidents: {summary.get('total_incidents', 0)}")
        by_severity = summary.get('by_severity', {})
        for severity in ["critical", "high", "medium", "low"]:
            count = by_severity.get(severity, 0)
            report.append(f"  {severity.upper()}: {count}")
        report.append("")
        
        # Service health
        if assessment.services:
            report.append("SERVICE HEALTH")
            report.append("-" * 70)
            for service in assessment.services:
                report.append(f"\n{service.service_name}")
                report.append(f"  Score: {service.health_score}/100 | Risk: {service.risk_level.upper()}")
                report.append(f"  Incidents: {service.total_incidents} total")
                report.append(f"    - Critical: {service.critical_incidents}")
                report.append(f"    - High: {service.high_incidents}")
                report.append(f"    - Medium: {service.medium_incidents}")
                report.append(f"  Trend: {service.incident_trend}")
            report.append("")
        
        # Critical areas
        if assessment.critical_areas:
            report.append("CRITICAL AREAS REQUIRING ATTENTION")
            report.append("-" * 70)
            for i, area in enumerate(assessment.critical_areas, 1):
                report.append(f"{i}. {area}")
            report.append("")
        
        # Recommendations
        if assessment.recommendations:
            report.append("RECOMMENDATIONS")
            report.append("-" * 70)
            for i, rec in enumerate(assessment.recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")
        
        report.append("=" * 70)
        report.append(f"Generated: {assessment.timestamp}")
        report.append("=" * 70)
        
        return "\n".join(report)
