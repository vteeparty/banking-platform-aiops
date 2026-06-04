#!/usr/bin/env python3
"""
Quick Start Guide - Refactored AI Log Analysis Module

Copy-paste ready examples for common scenarios.
"""

# ============================================================================
# SCENARIO 1: Parse a Jenkins Log and Find All Failures
# ============================================================================

def scenario_1_parse_jenkins_log():
    """Parse Jenkins log and print all detected failures"""
    from jenkins_log_parser import JenkinsLogParser
    
    # Parse the log
    parser = JenkinsLogParser("/path/to/jenkins-build.log")
    result = parser.parse()
    
    if result:
        print(f"Build Status: {result.build_status}")
        print(f"Total Lines: {result.total_lines}")
        print(f"\nFailures Found: {len(result.failures)}\n")
        
        for failure in result.failures:
            print(f"Line {failure.line_number}: {failure.failure_type.value}")
            print(f"  Error: {failure.error_line}")
            print(f"  Cause: {failure.root_cause}")
            print(f"  Fix: {failure.recommended_action}\n")


# ============================================================================
# SCENARIO 2: Create Incidents from Jenkins Log
# ============================================================================

def scenario_2_create_incidents():
    """Parse log and create incidents"""
    from jenkins_log_parser import JenkinsLogParser
    from incident_generator import IncidentGenerator
    
    # Parse
    parser = JenkinsLogParser("/path/to/jenkins-build.log")
    result = parser.parse()
    
    # Generate incidents
    gen = IncidentGenerator("incidents.json")
    incidents = gen.generate_from_parse_result(result)
    
    print(f"Created {len(incidents)} incidents:")
    for inc in incidents:
        print(f"  {inc.incident_id}: {inc.title} (Severity: {inc.severity})")


# ============================================================================
# SCENARIO 3: Check for Critical Issues
# ============================================================================

def scenario_3_find_critical_incidents():
    """Find and alert on critical incidents"""
    from incident_generator import IncidentGenerator, SeverityLevel
    
    gen = IncidentGenerator("incidents.json")
    critical = gen.get_incidents_by_severity(SeverityLevel.CRITICAL)
    
    if critical:
        print(f"⚠️  ALERT: {len(critical)} critical incident(s)!\n")
        for inc in critical:
            print(f"  {inc.incident_id}: {inc.title}")
            print(f"  Service: {inc.service}")
            print(f"  Root Cause: {inc.root_cause}\n")
        
        # Example: Send alert
        # send_slack_message(f"🔴 {len(critical)} critical incidents detected!")
    else:
        print("✅ No critical incidents")


# ============================================================================
# SCENARIO 4: Get Pipeline Health Report
# ============================================================================

def scenario_4_health_report():
    """Generate and display pipeline health report"""
    from health_assessment import HealthAssessment
    
    health = HealthAssessment("incidents.json")
    report = health.generate_report()
    print(report)
    
    # Save to file
    health.save_assessment("health_assessment.json")


# ============================================================================
# SCENARIO 5: Monitor Service-Specific Issues
# ============================================================================

def scenario_5_service_monitoring():
    """Get incidents for a specific service"""
    from incident_generator import IncidentGenerator
    
    gen = IncidentGenerator("incidents.json")
    
    # Get payment service incidents
    payment_incidents = gen.get_incidents_by_service("payment-service")
    
    print(f"Payment Service: {len(payment_incidents)} incidents")
    for inc in payment_incidents:
        icon = "🔴" if inc.severity == "critical" else "🟠" if inc.severity == "high" else "🟡"
        print(f"  {icon} {inc.incident_id}: {inc.title}")


# ============================================================================
# SCENARIO 6: Update Incident Status (Mark as Fixed)
# ============================================================================

def scenario_6_mark_fixed():
    """Mark incident as resolved"""
    from incident_generator import IncidentGenerator, IncidentStatus
    
    gen = IncidentGenerator("incidents.json")
    
    # Update status
    gen.update_incident_status(
        "INC-A1B2C3D4",
        IncidentStatus.RESOLVED,
        "Fixed by applying security patch X"
    )
    print("Incident marked as resolved")


# ============================================================================
# SCENARIO 7: Statistics and Summary
# ============================================================================

def scenario_7_statistics():
    """Get incident statistics"""
    from incident_generator import IncidentGenerator
    
    gen = IncidentGenerator("incidents.json")
    stats = gen.get_summary_stats()
    
    print("Incident Statistics:")
    print(f"  Total: {stats['total_incidents']}")
    print(f"  By Severity: {stats['by_severity']}")
    print(f"  By Type: {stats['by_failure_type']}")
    print(f"  By Service: {stats['by_service']}")
    print(f"  By Status: {stats['by_status']}")


# ============================================================================
# SCENARIO 8: Complete Automated Workflow
# ============================================================================

def scenario_8_full_automation():
    """Complete workflow: parse -> create incidents -> assess -> report"""
    from jenkins_log_parser import JenkinsLogParser
    from incident_generator import IncidentGenerator, SeverityLevel
    from health_assessment import HealthAssessment
    
    # 1. Parse Jenkins log
    print("Parsing Jenkins log...")
    parser = JenkinsLogParser("/path/to/jenkins-build.log")
    result = parser.parse()
    
    if not result:
        print("Failed to parse log")
        return
    
    print(f"  Status: {result.build_status}")
    print(f"  Failures: {len(result.failures)}")
    
    # 2. Generate incidents
    print("\nGenerating incidents...")
    gen = IncidentGenerator("incidents.json")
    incidents = gen.generate_from_parse_result(result)
    print(f"  Created: {len(incidents)} incidents")
    
    # 3. Check for critical issues
    critical = gen.get_incidents_by_severity(SeverityLevel.CRITICAL)
    if critical:
        print(f"  ⚠️  CRITICAL: {len(critical)} critical incident(s)")
    
    # 4. Assess health
    print("\nAssessing pipeline health...")
    health = HealthAssessment("incidents.json")
    assessment = health.assess()
    print(f"  Status: {assessment.health_status.upper()}")
    print(f"  Score: {assessment.overall_health_score}/100")
    print(f"  Risk: {assessment.overall_risk_level.upper()}")
    
    # 5. Generate report
    print("\nGenerating report...")
    report = health.generate_report()
    print(report)
    
    # 6. Save assessment
    health.save_assessment("health_assessment.json")
    print("\nResults saved to incidents.json and health_assessment.json")


# ============================================================================
# SCENARIO 9: CI/CD Integration (Jenkins Pipeline)
# ============================================================================

def scenario_9_jenkins_integration():
    """
    Example for Jenkins pipeline integration.
    
    Usage in Jenkinsfile:
    
    stage('Log Analysis') {
        steps {
            script {
                sh '''
                    python3 -c "
                    from jenkins_log_parser import JenkinsLogParser
                    from incident_generator import IncidentGenerator
                    from health_assessment import HealthAssessment
                    
                    parser = JenkinsLogParser(buildLog)
                    result = parser.parse()
                    
                    gen = IncidentGenerator('incidents.json')
                    gen.generate_from_parse_result(result)
                    
                    health = HealthAssessment('incidents.json')
                    health.save_assessment()
                    "
                '''
            }
        }
    }
    """
    pass


# ============================================================================
# SCENARIO 10: Integration with Slack/Teams
# ============================================================================

def scenario_10_notification_integration():
    """Example of sending notifications"""
    from incident_generator import IncidentGenerator, SeverityLevel
    from health_assessment import HealthAssessment
    
    gen = IncidentGenerator("incidents.json")
    health = HealthAssessment("incidents.json")
    
    # Get critical incidents
    critical = gen.get_incidents_by_severity(SeverityLevel.CRITICAL)
    
    # Build message
    if critical:
        message = f"🔴 CRITICAL: {len(critical)} critical incident(s) detected\n"
        for inc in critical[:3]:  # Top 3
            message += f"• {inc.title}\n"
        
        # Example: Send to Slack
        # send_slack_message(message)
        print(message)
    
    # Get health summary
    assessment = health.assess()
    health_msg = f"📊 Pipeline Health: {assessment.overall_health_score}/100 ({assessment.health_status.upper()})"
    print(health_msg)
    
    # Example: Send to Teams
    # send_teams_message(health_msg)


# ============================================================================
# FILE STRUCTURE
# ============================================================================

"""
Where files are created:

incidents.json               - All generated incidents (persistent)
health_assessment.json       - Health assessment results
jenkins-build.log           - Your Jenkins console log (input)

After running:
├── incidents.json                   # Grows over time as you run
├── health_assessment.json           # Updated each assessment
└── jenkins-logs/
    └── build-123.log               # Your original Jenkins logs
"""


# ============================================================================
# COMMAND LINE USAGE
# ============================================================================

"""
Parse and process a Jenkins log:

    python production_integration.py /path/to/jenkins-build.log

Run tests:

    python test_refactored_module.py

Generate health report:

    python -c "
    from health_assessment import HealthAssessment
    health = HealthAssessment('incidents.json')
    print(health.generate_report())
    "

Query incidents:

    python -c "
    from incident_generator import IncidentGenerator, SeverityLevel
    gen = IncidentGenerator('incidents.json')
    critical = gen.get_incidents_by_severity(SeverityLevel.CRITICAL)
    for inc in critical:
        print(inc.incident_id, inc.title)
    "
"""


# ============================================================================
# KEY IMPORTS
# ============================================================================

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
"""


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     AI LOG ANALYSIS - QUICK START EXAMPLES                ║
    ╚════════════════════════════════════════════════════════════╝
    
    Available scenarios:
    1. Parse Jenkins log and find all failures
    2. Create incidents from Jenkins log  
    3. Check for critical issues
    4. Generate health report
    5. Monitor service-specific issues
    6. Mark incident as fixed
    7. Get statistics
    8. Full automated workflow
    9. CI/CD Jenkins integration
    10. Slack/Teams notifications
    
    To run a scenario:
    
        python quick_start.py
        
    Then uncomment the scenario function at the bottom and run it.
    """)
    
    # Uncomment to run a scenario:
    # scenario_1_parse_jenkins_log()
    # scenario_2_create_incidents()
    # scenario_3_find_critical_incidents()
    # scenario_4_health_report()
    # scenario_8_full_automation()
