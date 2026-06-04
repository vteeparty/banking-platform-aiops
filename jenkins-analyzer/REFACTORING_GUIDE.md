#!/usr/bin/env python3
"""
REFACTORED AI LOG ANALYSIS MODULE

Production-ready implementation guide and API reference.

This module provides:
1. jenkins_log_parser.py - Parse and analyze Jenkins console logs
2. incident_generator.py - Convert failures into structured incidents
3. health_assessment.py - Assess overall pipeline health
4. production_integration.py - Example integration workflow

REMOVED:
- All mock data and sample JSON files
- Sample Jenkins log usage
- In-memory testing data
"""

from jenkins_log_parser import (
    JenkinsLogParser,
    FailureType,
    ParseResult,
    ParsedFailure,
)

from incident_generator import (
    IncidentGenerator,
    Incident,
    SeverityLevel,
    IncidentStatus,
)

from health_assessment import (
    HealthAssessment,
    PipelineHealth,
    ServiceHealth,
    HealthStatus,
    RiskLevel,
)


# ============================================================================
# QUICK START GUIDE
# ============================================================================

def example_parse_and_generate_incidents():
    """
    Example: Parse Jenkins log and generate incidents
    """
    # 1. Parse Jenkins console log
    parser = JenkinsLogParser("/path/to/jenkins-build.log")
    parse_result = parser.parse()
    
    if parse_result:
        print(f"Build Status: {parse_result.build_status}")
        print(f"Failures: {len(parse_result.failures)}")
        
        # 2. Generate incidents from failures
        incident_gen = IncidentGenerator("incidents.json")
        incidents = incident_gen.generate_from_parse_result(parse_result)
        
        # Access incidents
        for incident in incidents:
            print(f"Incident {incident.incident_id}: {incident.title}")
            print(f"  Severity: {incident.severity}")
            print(f"  Service: {incident.service}")
            print(f"  Root Cause: {incident.root_cause}")


def example_query_incidents():
    """
    Example: Query incidents
    """
    incident_gen = IncidentGenerator("incidents.json")
    
    # Get open incidents
    open_incidents = incident_gen.get_open_incidents()
    
    # Get critical incidents
    critical = incident_gen.get_incidents_by_severity(SeverityLevel.CRITICAL)
    
    # Get service-specific incidents
    payment_incidents = incident_gen.get_incidents_by_service("payment-service")
    
    # Update incident status
    incident_gen.update_incident_status(
        "INC-XXXXX",
        IncidentStatus.RESOLVED,
        notes="Fixed by applying patch X"
    )


def example_health_assessment():
    """
    Example: Assess pipeline health
    """
    health = HealthAssessment("incidents.json")
    
    # Get full assessment
    assessment = health.assess()
    
    print(f"Health: {assessment.health_status}")
    print(f"Score: {assessment.overall_health_score}/100")
    print(f"Risk: {assessment.overall_risk_level}")
    
    # Save to file
    health.save_assessment("health_assessment.json")
    
    # Generate text report
    report = health.generate_report()
    print(report)


# ============================================================================
# MODULE API REFERENCE
# ============================================================================

"""
JENKINS LOG PARSER
==================

JenkinsLogParser(log_file_path: str)
  
  Methods:
  - parse() -> ParseResult | None
      Parse Jenkins console log and return failures
  
  - extract_build_metrics() -> Dict
      Extract duration, error count, test results, etc.

ParseResult:
  - log_file: str - Path to log file
  - total_lines: int - Total lines in log
  - build_status: str - SUCCESS, FAILURE, ABORTED, UNKNOWN
  - failures: List[ParsedFailure] - Detected failures

ParsedFailure:
  - failure_type: FailureType - Maven, SonarQube, Trivy, K8s
  - line_number: int - Line where failure detected
  - error_line: str - The actual error message
  - root_cause: str - Human-readable cause
  - recommended_action: str - What to do to fix
  - context_lines: List[str] - Surrounding lines

Detects:
  ✓ Maven compilation errors, dependency issues, test failures
  ✓ SonarQube quality gate failures, coverage issues
  ✓ Trivy security vulnerabilities
  ✓ Kubernetes deployment failures (ImagePullBackOff, etc.)


INCIDENT GENERATOR
==================

IncidentGenerator(incidents_file: str = "incidents.json")

  Methods:
  - generate_from_parse_result(parse_result) -> List[Incident]
      Convert parsed failures to incidents
  
  - get_incident(incident_id: str) -> Incident | None
      Retrieve incident by ID
  
  - get_open_incidents() -> List[Incident]
      Get all open incidents
  
  - get_incidents_by_severity(severity) -> List[Incident]
      Filter by severity level
  
  - get_incidents_by_service(service: str) -> List[Incident]
      Get incidents for specific service
  
  - update_incident_status(id, status, notes) -> bool
      Update incident and resolution notes
  
  - get_summary_stats() -> Dict
      Get counts by severity, type, service, status
  
  - save() -> None
      Persist incidents to JSON file

Incident:
  - incident_id: str - Unique ID (INC-XXXXXXXX)
  - created_at: str - ISO 8601 timestamp
  - failure_type: str - Maven, SonarQube, Trivy, K8s
  - severity: str - Critical, High, Medium, Low
  - status: str - Open, In Progress, Resolved, Closed, Ignored
  - service: str | None - Affected service (if detected)
  - title: str - Human-readable summary
  - description: str - Detailed description
  - root_cause: str - What caused the issue
  - recommended_action: str - How to fix
  - build_log: str - Path to originating log file
  - build_status: str - Overall build status


HEALTH ASSESSMENT
=================

HealthAssessment(incidents_file: str = "incidents.json")

  Methods:
  - assess() -> PipelineHealth
      Run full health assessment
  
  - save_assessment(output_file: str) -> None
      Save to JSON file
  
  - generate_report() -> str
      Generate human-readable report

PipelineHealth:
  - health_status: str - Healthy, Degraded, Unhealthy, Critical
  - overall_health_score: int - 0-100
  - overall_risk_level: str - Low, Medium, High, Critical
  - build_success_rate: float - 0-100%
  - mean_time_to_recovery: str | None - Average fix time
  - services: List[ServiceHealth] - Per-service metrics
  - critical_areas: List[str] - Areas needing attention
  - recommendations: List[str] - Actionable recommendations

ServiceHealth:
  - service_name: str
  - total_incidents: int
  - critical_incidents: int
  - high_incidents: int
  - open_incidents: int
  - incident_trend: str - increasing, stable, decreasing
  - health_score: int - 0-100
  - risk_level: str
  - recommendations: List[str]


TYPICAL WORKFLOW
================

1. Parse Jenkins Log
   parser = JenkinsLogParser("jenkins-build.log")
   result = parser.parse()

2. Generate Incidents
   gen = IncidentGenerator("incidents.json")
   incidents = gen.generate_from_parse_result(result)

3. Query Results
   critical = gen.get_incidents_by_severity(SeverityLevel.CRITICAL)
   payment_issues = gen.get_incidents_by_service("payment-service")

4. Assess Health
   health = HealthAssessment("incidents.json")
   assessment = health.assess()
   print(health.generate_report())

5. Update Status
   gen.update_incident_status("INC-XXXXX", IncidentStatus.RESOLVED)
   gen.save()


JSON STORAGE FORMAT
===================

incidents.json (array of incidents):
[
  {
    "incident_id": "INC-A1B2C3D4",
    "created_at": "2026-06-04T10:30:45Z",
    "failure_type": "maven_build",
    "severity": "critical",
    "status": "open",
    "service": "payment-service",
    "title": "Maven build failed in payment-service",
    "description": "...",
    "root_cause": "Java compilation error",
    "recommended_action": "Fix compilation errors, check imports",
    "error_line": "[ERROR] cannot find symbol",
    "context": "...",
    "build_log": "/path/to/jenkins-build.log",
    "build_status": "FAILURE",
    "metrics": {...},
    "tags": ["maven_build", "service:payment-service", "java"],
    "assigned_to": null,
    "resolution_notes": null,
    "updated_at": null
  }
]

health_assessment.json:
{
  "timestamp": "2026-06-04T10:31:00Z",
  "health_status": "degraded",
  "overall_health_score": 65,
  "overall_risk_level": "high",
  "build_success_rate": 78.5,
  "mean_time_to_recovery": "2h 15m",
  "services": [...],
  "critical_areas": [...],
  "recommendations": [...],
  "incident_summary": {...}
}


KEY IMPROVEMENTS OVER OLD IMPLEMENTATION
========================================

✓ No more mock data - pure production processing
✓ Real Jenkins log parsing (not sample files)
✓ Accurate failure detection (Maven, SonarQube, Trivy, K8s)
✓ JSON-based persistence (easy integration)
✓ Service extraction and tracking
✓ Health scoring algorithm
✓ Trend analysis
✓ Severity classification with remediation
✓ Clean, maintainable code
✓ Comprehensive API for querying


INTEGRATION POINTS
==================

- CI/CD Pipeline: Trigger on build completion
- Notification System: Alert on critical incidents
- Monitoring Dashboard: Display health metrics
- Incident Tracking: Export to JIRA, ServiceNow, etc.
- Reporting: Daily/weekly health summaries
"""


if __name__ == "__main__":
    print(__doc__)
