#!/usr/bin/env python3
"""
Production Integration Example for AI Log Analysis Module

Shows how to:
1. Parse real Jenkins console logs
2. Generate incidents
3. Assess pipeline health
4. Export results

No mock data - works with actual Jenkins logs.
"""

import sys
from pathlib import Path

from jenkins_log_parser import JenkinsLogParser
from incident_generator import IncidentGenerator, SeverityLevel, IncidentStatus
from health_assessment import HealthAssessment


def main():
    """Main integration workflow"""
    
    # Example usage with a real Jenkins log file
    if len(sys.argv) < 2:
        print("Usage: python production_integration.py <jenkins_log_file>")
        print("\nExample:")
        print("  python production_integration.py /path/to/jenkins-build.log")
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    if not Path(log_file).exists():
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)
    
    print("=" * 70)
    print("AI LOG ANALYSIS MODULE - PRODUCTION WORKFLOW")
    print("=" * 70)
    print()
    
    # Step 1: Parse Jenkins Log
    print("[1/4] Parsing Jenkins console log...")
    parser = JenkinsLogParser(log_file)
    parse_result = parser.parse()
    
    if parse_result is None:
        print("Error: Failed to parse log file")
        sys.exit(1)
    
    print(f"✓ Parsed {parse_result.total_lines} lines from {Path(log_file).name}")
    print(f"  Build Status: {parse_result.build_status}")
    print(f"  Failures Detected: {len(parse_result.failures)}")
    
    # Extract and display metrics
    metrics = parser.extract_build_metrics()
    print(f"\n  Build Metrics:")
    print(f"    - Duration: {metrics['build_duration']}")
    print(f"    - Errors: {metrics['error_count']}")
    print(f"    - Warnings: {metrics['warning_count']}")
    if metrics['tests']:
        print(f"    - Tests: {metrics['tests']['total']} run, "
              f"{metrics['tests']['failures']} failed, "
              f"{metrics['tests']['errors']} errors")
    
    print()
    
    # Step 2: Generate Incidents
    print("[2/4] Generating incidents from failures...")
    incident_gen = IncidentGenerator("incidents.json")
    incidents = incident_gen.generate_from_parse_result(parse_result)
    
    print(f"✓ Created {len(incidents)} incident(s)")
    for incident in incidents:
        severity_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }.get(incident.severity, "")
        
        print(f"\n  {severity_icon} {incident.incident_id}: {incident.title}")
        print(f"     Type: {incident.failure_type}")
        print(f"     Severity: {incident.severity.upper()}")
        print(f"     Service: {incident.service or 'Unknown'}")
        print(f"     Root Cause: {incident.root_cause}")
        print(f"     Action: {incident.recommended_action}")
    
    print()
    
    # Step 3: Generate Summary Statistics
    print("[3/4] Generating incident summary...")
    summary = incident_gen.get_summary_stats()
    print(f"✓ Incident Summary:")
    print(f"    - Total: {summary['total_incidents']}")
    print(f"    - By Severity: {summary['by_severity']}")
    print(f"    - By Type: {summary['by_failure_type']}")
    print(f"    - By Status: {summary['by_status']}")
    
    print()
    
    # Step 4: Assess Pipeline Health
    print("[4/4] Assessing pipeline health...")
    health = HealthAssessment("incidents.json")
    assessment = health.assess()
    
    print(f"✓ Health Assessment Complete")
    print(f"    - Status: {assessment.health_status.upper()}")
    print(f"    - Score: {assessment.overall_health_score}/100")
    print(f"    - Risk: {assessment.overall_risk_level.upper()}")
    print(f"    - Success Rate: {assessment.build_success_rate:.1f}%")
    
    if assessment.critical_areas:
        print(f"\n    Critical Areas:")
        for area in assessment.critical_areas[:3]:
            print(f"      • {area}")
    
    if assessment.recommendations:
        print(f"\n    Recommendations:")
        for rec in assessment.recommendations[:3]:
            print(f"      • {rec}")
    
    print()
    print("=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"\nResults saved to:")
    print(f"  • incidents.json (incident database)")
    print(f"\nTo view detailed health report:")
    print(f"  health_assessment.save_assessment('health_assessment.json')")
    print(f"\nTo query incidents:")
    print(f"  open_incidents = incident_gen.get_open_incidents()")
    print(f"  critical = incident_gen.get_incidents_by_severity(SeverityLevel.CRITICAL)")
    print()


if __name__ == "__main__":
    main()
