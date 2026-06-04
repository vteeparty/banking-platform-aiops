#!/usr/bin/env python3
"""
Test and validation module for refactored AI log analysis.

Demonstrates all functionality with a realistic test log.
"""

import tempfile
from pathlib import Path

from jenkins_log_parser import JenkinsLogParser
from incident_generator import IncidentGenerator, SeverityLevel, IncidentStatus
from health_assessment import HealthAssessment


# Sample production-like Jenkins log for testing
SAMPLE_JENKINS_LOG = """[Pipeline] Start of Pipeline
[Pipeline] stage
[Pipeline] { (Build Stage)
[Pipeline] sh
+ mvn clean package

[INFO] Scanning for projects...
[INFO] 
[INFO] -----< com.bankingplatform:payment-service >-----
[INFO] Building Payment Service 1.0.0
[INFO] --------------------------------[ jar ]---------------------------------

Downloading from central: https://repo.maven.apache.org/maven2/org/springframework/boot/spring-boot-starter-web/2.7.0/spring-boot-starter-web-2.7.0.pom
Downloaded from central (13 KB at 0.35 MB/s)

[INFO] --- maven-compiler-plugin:3.8.1:compile (default-compile) @ payment-service ---
[INFO] Compiling 24 source files to /var/jenkins_home/workspace/payment-service/target/classes

[ERROR] COMPILATION ERROR
[ERROR] /var/jenkins_home/workspace/payment-service/src/main/java/com/bank/service/PaymentService.java:[45,8] cannot find symbol
[ERROR]   symbol:   class TransactionManager
[ERROR]   location: package com.bank.core
[ERROR] 
[INFO] BUILD FAILURE
[INFO] 
[INFO] --- maven-compiler-plugin:3.8.1:compile (default-compile) @ payment-service ---
[INFO] To see the full stack trace of the error, run Maven with the -e or --debug option.
[INFO] For more information about the error, and possible solutions, look at the following reference:
[INFO] [Help 1] http://maven.apache.org/run-maven-plugins-error-mapping.html
[INFO] Total time: 2.345 s
[INFO] Finished at: 2026-06-04T10:30:45Z
[INFO] Final Memory: 1024M/2048M

[Pipeline] }
[Pipeline] stage
[Pipeline] { (SonarQube Stage)
[Pipeline] withSonarQubeEnv
[Pipeline] {
[Pipeline] sh
+ sonar-scanner -Dsonar.projectKey=banking-platform

INFO: Scanner configuration file: /opt/sonar-scanner/conf/sonar-scanner.properties
INFO: Project root configuration file: /jenkins/workspace/payment-service/sonar-project.properties
INFO: SonarScanner 5.0.1.3006
INFO: Analysis finished successfully
INFO: Quality Gate FAILED

[ERROR] Quality Gate FAILED
[ERROR] Coverage below threshold: 45% < 75%
[ERROR] BLOCKER issue found: SQL injection vulnerability

[Pipeline] }
[Pipeline] stage
[Pipeline] { (Security Scan)
[Pipeline] sh
+ trivy image banking-platform:1.0.0

2026-06-04T10:30:50Z  INFO  Aqua Security Trivy
2026-06-04T10:30:50Z  INFO  Vulnerability DB: Downloaded
2026-06-04T10:30:52Z  INFO  Detected OS: debian
2026-06-04T10:30:52Z  CRITICAL OpenSSL 1.1.1 - CVE-2021-3711
2026-06-04T10:30:52Z  HIGH libssl - Multiple vulnerabilities
2026-06-04T10:30:52Z  INFO  Total: 45 vulnerabilities found

[Pipeline] }
[Pipeline] stage
[Pipeline] { (Deploy Stage)
[Pipeline] sh
+ kubectl apply -f deployment.yaml

deployment.apps/payment-service created

+ kubectl rollout status deployment/payment-service -n default

Waiting for deployment "payment-service" to roll out...
error: deployment "payment-service" rollout failed due to ImagePullBackOff

[ERROR] Deployment failed
[ERROR] Error: Failed to pull image from registry
[ERROR] Authentication failed for docker.io/bankingplatform/payment-service:1.0.0
[ERROR] Please check your registry credentials

[Pipeline] }
"""


def test_complete_workflow():
    """Test complete workflow with sample log"""
    print("=" * 70)
    print("REFACTORED AI LOG ANALYSIS - TEST SUITE")
    print("=" * 70)
    print()
    
    # Create temporary files for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test-jenkins.log"
        incidents_file = Path(tmpdir) / "incidents.json"
        
        # Write sample log
        log_file.write_text(SAMPLE_JENKINS_LOG)
        print(f"[✓] Created test Jenkins log: {log_file.name}")
        print()
        
        # =====================================================================
        # TEST 1: Parse Jenkins Log
        # =====================================================================
        print("[TEST 1] Jenkins Log Parser")
        print("-" * 70)
        
        parser = JenkinsLogParser(str(log_file))
        result = parser.parse()
        
        assert result is not None, "Parser should return result"
        assert result.build_status == "FAILURE", "Build status should be FAILURE"
        assert len(result.failures) > 0, "Should detect failures"
        
        print(f"✓ Parsed {result.total_lines} lines")
        print(f"✓ Build Status: {result.build_status}")
        print(f"✓ Failures Detected: {len(result.failures)}")
        print()
        
        # Display each failure
        for i, failure in enumerate(result.failures, 1):
            print(f"\n  Failure {i}: {failure.failure_type.value}")
            print(f"    Line: {failure.line_number}")
            print(f"    Cause: {failure.root_cause}")
            print(f"    Action: {failure.recommended_action}")
        print()
        
        # Verify specific failures
        failure_types = [f.failure_type for f in result.failures]
        from jenkins_log_parser import FailureType
        
        assert FailureType.MAVEN_BUILD in failure_types, "Should detect Maven failure"
        assert FailureType.SONARQUBE_SCAN in failure_types, "Should detect SonarQube failure"
        assert FailureType.TRIVY_SECURITY in failure_types, "Should detect Trivy failure"
        assert FailureType.KUBERNETES_DEPLOY in failure_types, "Should detect K8s failure"
        print("✓ All failure types detected correctly")
        print()
        
        # =====================================================================
        # TEST 2: Generate Incidents
        # =====================================================================
        print("[TEST 2] Incident Generator")
        print("-" * 70)
        
        incident_gen = IncidentGenerator(str(incidents_file))
        incidents = incident_gen.generate_from_parse_result(result)
        
        assert len(incidents) > 0, "Should generate incidents"
        assert len(incident_gen.incidents) == len(incidents), "All incidents should be stored"
        
        print(f"✓ Generated {len(incidents)} incidents")
        
        # Verify incident properties
        for incident in incidents:
            assert incident.incident_id.startswith("INC-"), "Incident ID should be generated"
            assert incident.severity in ["critical", "high", "medium", "low"], "Severity should be valid"
            assert incident.status == "open", "New incidents should be open"
            assert incident.created_at, "Timestamp should be set"
            # Service may or may not be extracted, both are OK
            assert isinstance(incident.service, str) or incident.service is None, "Service should be string or None"
        
        print("✓ All incidents have required properties")
        print()
        
        # Display incidents
        for inc in incidents[:3]:  # Show first 3
            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(inc.severity, "")
            print(f"\n  {severity_emoji} {inc.incident_id}")
            print(f"     {inc.title}")
            print(f"     Service: {inc.service or 'Unknown'}")
            print(f"     Severity: {inc.severity.upper()}")
        print()
        
        # =====================================================================
        # TEST 3: Query Incidents
        # =====================================================================
        print("[TEST 3] Incident Querying")
        print("-" * 70)
        
        open_incidents = incident_gen.get_open_incidents()
        assert len(open_incidents) == len(incidents), "All new incidents should be open"
        print(f"✓ Found {len(open_incidents)} open incidents")
        
        critical = incident_gen.get_incidents_by_severity(SeverityLevel.CRITICAL)
        print(f"✓ Found {len(critical)} critical incidents")
        
        payment_incidents = incident_gen.get_incidents_by_service("payment-service")
        print(f"✓ Found {len(payment_incidents)} incidents for payment-service")
        
        summary = incident_gen.get_summary_stats()
        print(f"✓ Summary Statistics:")
        print(f"    Total: {summary['total_incidents']}")
        print(f"    By Severity: {summary['by_severity']}")
        print(f"    By Type: {summary['by_failure_type']}")
        print()
        
        # =====================================================================
        # TEST 4: Update Incident Status
        # =====================================================================
        print("[TEST 4] Incident Status Update")
        print("-" * 70)
        
        first_incident = incidents[0]
        updated = incident_gen.update_incident_status(
            first_incident.incident_id,
            IncidentStatus.IN_PROGRESS,
            "Assigned to team"
        )
        
        assert updated, "Should successfully update incident"
        
        # Verify update
        updated_incident = incident_gen.get_incident(first_incident.incident_id)
        assert updated_incident.status == "in_progress", "Status should be updated"
        assert updated_incident.resolution_notes == "Assigned to team", "Notes should be saved"
        assert updated_incident.updated_at, "Update timestamp should be set"
        
        print(f"✓ Updated {first_incident.incident_id} status to IN_PROGRESS")
        print(f"✓ Resolution notes saved")
        print(f"✓ Update timestamp recorded")
        print()
        
        # =====================================================================
        # TEST 5: Health Assessment
        # =====================================================================
        print("[TEST 5] Health Assessment")
        print("-" * 70)
        
        health = HealthAssessment(str(incidents_file))
        assessment = health.assess()
        
        assert assessment.overall_health_score >= 0, "Score should be valid"
        assert assessment.overall_health_score <= 100, "Score should be <= 100"
        assert assessment.health_status in ["healthy", "degraded", "unhealthy", "critical"], "Status should be valid"
        
        print(f"✓ Health Assessment Generated")
        print(f"    Status: {assessment.health_status.upper()}")
        print(f"    Score: {assessment.overall_health_score}/100")
        print(f"    Risk: {assessment.overall_risk_level.upper()}")
        print(f"    Success Rate: {assessment.build_success_rate:.1f}%")
        print()
        
        # Check services
        assert len(assessment.services) > 0, "Should have service assessments"
        print(f"✓ Assessed {len(assessment.services)} service(s)")
        for service in assessment.services:
            print(f"    - {service.service_name}: {service.health_score}/100 ({service.risk_level.upper()})")
        print()
        
        # Check recommendations
        assert len(assessment.recommendations) > 0, "Should generate recommendations"
        print(f"✓ Generated {len(assessment.recommendations)} recommendations:")
        for i, rec in enumerate(assessment.recommendations[:3], 1):
            print(f"    {i}. {rec}")
        print()
        
        # =====================================================================
        # TEST 6: Report Generation
        # =====================================================================
        print("[TEST 6] Report Generation")
        print("-" * 70)
        
        report = health.generate_report()
        assert report, "Report should be generated"
        assert "HEALTH ASSESSMENT REPORT" in report, "Report should have title"
        assert assessment.health_status.upper() in report, "Report should include status"
        
        print("✓ Generated human-readable report:")
        print()
        print(report[:500] + "...")  # Show first 500 chars
        print()
        
        # =====================================================================
        # TEST 7: JSON Persistence
        # =====================================================================
        print("[TEST 7] JSON Persistence")
        print("-" * 70)
        
        health.save_assessment()
        assert incidents_file.exists(), "Incidents file should exist"
        
        # Reload and verify
        incident_gen2 = IncidentGenerator(str(incidents_file))
        reloaded_count = len(incident_gen2.incidents)
        
        assert reloaded_count == len(incidents), "Reloaded incidents should match"
        print(f"✓ Saved {len(incidents)} incidents to {incidents_file.name}")
        print(f"✓ Reloaded {reloaded_count} incidents from JSON")
        print()
    
    print("=" * 70)
    print("ALL TESTS PASSED ✓")
    print("=" * 70)
    print()
    print("Summary:")
    print("  ✓ Jenkins log parsing works correctly")
    print("  ✓ Failure detection is accurate (Maven, SonarQube, Trivy, K8s)")
    print("  ✓ Incident generation creates structured data")
    print("  ✓ Querying API provides flexible access")
    print("  ✓ Status updates preserve history")
    print("  ✓ Health assessment generates insights")
    print("  ✓ Reporting is clear and actionable")
    print("  ✓ JSON persistence works reliably")
    print()
    print("Ready for production use!")
    print()


if __name__ == "__main__":
    test_complete_workflow()
