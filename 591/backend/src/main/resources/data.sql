INSERT INTO repositories (id, name, full_name, html_url, default_branch, build_tool, last_scan_time, scan_status, health_score, created_at, updated_at) VALUES
(1, 'user-service', 'myorg/user-service', 'https://github.com/myorg/user-service', 'main', 'MAVEN', '2026-05-29T10:30:00', 'COMPLETED', 72.5, '2026-05-20T08:00:00', '2026-05-29T10:30:00'),
(2, 'order-service', 'myorg/order-service', 'https://github.com/myorg/order-service', 'main', 'MAVEN', '2026-05-28T14:20:00', 'COMPLETED', 58.0, '2026-05-18T09:15:00', '2026-05-28T14:20:00'),
(3, 'payment-gateway', 'myorg/payment-gateway', 'https://github.com/myorg/payment-gateway', 'develop', 'GRADLE', '2026-05-29T16:45:00', 'COMPLETED', 85.0, '2026-05-22T11:30:00', '2026-05-29T16:45:00');

INSERT INTO scan_results (id, repo_id, scan_time, status, total_deps, conflict_count, vulnerability_count, outdated_count) VALUES
(1, 1, '2026-05-29T10:30:00', 'COMPLETED', 5, 1, 2, 3),
(2, 2, '2026-05-28T14:20:00', 'COMPLETED', 5, 2, 3, 2);

INSERT INTO dependency_records (id, scan_id, group_id, artifact_id, version, latest_version, scope, is_direct, is_outdated) VALUES
(1, 1, 'org.springframework.boot', 'spring-boot-starter-web', '3.1.5', '3.2.5', 'compile', true, true),
(2, 1, 'org.springframework.boot', 'spring-boot-starter-data-jpa', '3.1.5', '3.2.5', 'compile', true, true),
(3, 1, 'com.google.guava', 'guava', '32.1.2-jre', '33.0.0-jre', 'compile', true, true),
(4, 1, 'org.postgresql', 'postgresql', '42.6.0', '42.7.3', 'runtime', true, false),
(5, 1, 'com.fasterxml.jackson.core', 'jackson-databind', '2.15.2', '2.17.0', 'compile', false, true),
(6, 2, 'org.springframework.boot', 'spring-boot-starter-web', '3.0.9', '3.2.5', 'compile', true, true),
(7, 2, 'org.springframework.boot', 'spring-boot-starter-data-jpa', '3.0.9', '3.2.5', 'compile', true, true),
(8, 2, 'com.google.guava', 'guava', '31.1-jre', '33.0.0-jre', 'compile', true, true),
(9, 2, 'org.postgresql', 'postgresql', '42.5.4', '42.7.3', 'runtime', true, false),
(10, 2, 'org.apache.commons', 'commons-lang3', '3.12.0', '3.14.0', 'compile', true, true);

INSERT INTO vulnerability_records (id, scan_id, cve_id, severity, cvss_score, description, affected_version, fixed_version, group_id, artifact_id) VALUES
(1, 1, 'CVE-2024-0001', 'HIGH', 7.5, 'SQL Injection vulnerability in Spring Data JPA', '3.1.5', '3.2.0', 'org.springframework.boot', 'spring-boot-starter-data-jpa'),
(2, 1, 'CVE-2024-0002', 'MEDIUM', 5.3, 'Denial of Service in Jackson Databind deserialization', '2.15.2', '2.16.0', 'com.fasterxml.jackson.core', 'jackson-databind'),
(3, 2, 'CVE-2023-44487', 'CRITICAL', 9.8, 'HTTP/2 Rapid Reset Attack vulnerability', '3.0.9', '3.1.0', 'org.springframework.boot', 'spring-boot-starter-web'),
(4, 2, 'CVE-2024-0003', 'HIGH', 7.8, 'Path traversal vulnerability in Spring MVC', '3.0.9', '3.1.2', 'org.springframework.boot', 'spring-boot-starter-web'),
(5, 2, 'CVE-2024-0004', 'LOW', 3.1, 'Information disclosure in Guava cache', '31.1-jre', '32.0.0-jre', 'com.google.guava', 'guava');

INSERT INTO upgrade_suggestion_records (id, repo_id, group_id, artifact_id, current_version, target_version, upgrade_type, risk_level, compatibility_score, breaking_changes) VALUES
(1, 1, 'org.springframework.boot', 'spring-boot-starter-web', '3.1.5', '3.2.5', 'MINOR', 'LOW_RISK', 85.0, 'Minor version upgrade - new features added, backward compatible; Check deprecation notices in release notes'),
(2, 1, 'org.springframework.boot', 'spring-boot-starter-data-jpa', '3.1.5', '3.2.5', 'MINOR', 'LOW_RISK', 85.0, 'Minor version upgrade - new features added, backward compatible; Check deprecation notices in release notes'),
(3, 1, 'com.google.guava', 'guava', '32.1.2-jre', '33.0.0-jre', 'MAJOR', 'MEDIUM_RISK', 55.0, 'Major version upgrade may contain API incompatibilities; Review migration guide before upgrading'),
(4, 1, 'com.fasterxml.jackson.core', 'jackson-databind', '2.15.2', '2.17.0', 'MINOR', 'MEDIUM_RISK', 70.0, 'Minor version upgrade - new features added, backward compatible; Check deprecation notices in release notes; Jackson major upgrade may change serialization behavior'),
(5, 2, 'org.springframework.boot', 'spring-boot-starter-web', '3.0.9', '3.2.5', 'MINOR', 'MEDIUM_RISK', 65.0, 'Minor version upgrade - new features added, backward compatible; Check deprecation notices in release notes'),
(6, 2, 'org.springframework.boot', 'spring-boot-starter-data-jpa', '3.0.9', '3.2.5', 'MINOR', 'MEDIUM_RISK', 65.0, 'Minor version upgrade - new features added, backward compatible; Check deprecation notices in release notes'),
(7, 2, 'com.google.guava', 'guava', '31.1-jre', '33.0.0-jre', 'MAJOR', 'HIGH_RISK', 40.0, 'Major version upgrade may contain API incompatibilities; Review migration guide before upgrading'),
(8, 2, 'org.apache.commons', 'commons-lang3', '3.12.0', '3.14.0', 'MINOR', 'SAFE', 92.0, 'Minor version upgrade - new features added, backward compatible; Check deprecation notices in release notes');
