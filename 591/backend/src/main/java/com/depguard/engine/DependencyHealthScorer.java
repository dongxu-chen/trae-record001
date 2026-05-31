package com.depguard.engine;

import com.depguard.entity.DependencyRecord;
import com.depguard.entity.VulnerabilityRecord;
import com.depguard.repository.VulnerabilityRecordRepository;
import com.depguard.service.DependencyParserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@RequiredArgsConstructor
public class DependencyHealthScorer {

    private final VulnerabilityRecordRepository vulnerabilityRecordRepository;
    private final DependencyParserService dependencyParserService;

    private static final Map<String, Double> POPULARITY_CACHE = new ConcurrentHashMap<>();

    public HealthScore calculateHealthScore(DependencyRecord dependency) {
        String key = dependency.getGroupId() + ":" + dependency.getArtifactId() + ":" + dependency.getVersion();

        double vulnerabilityScore = calculateVulnerabilityScore(dependency);
        double freshnessScore = calculateFreshnessScore(dependency);
        double popularityScore = calculatePopularityScore(dependency);

        double overallScore = 0.4 * vulnerabilityScore + 0.35 * freshnessScore + 0.25 * popularityScore;

        String grade = getGrade(overallScore);
        List<String> recommendations = generateRecommendations(dependency, vulnerabilityScore, freshnessScore, popularityScore);

        return new HealthScore(
                key,
                overallScore,
                grade,
                vulnerabilityScore,
                freshnessScore,
                popularityScore,
                recommendations
        );
    }

    private double calculateVulnerabilityScore(DependencyRecord dependency) {
        List<VulnerabilityRecord> vulns = vulnerabilityRecordRepository
                .findByGroupIdAndArtifactId(dependency.getGroupId(), dependency.getArtifactId());

        if (vulns.isEmpty()) {
            return 100.0;
        }

        double score = 100.0;
        for (VulnerabilityRecord vuln : vulns) {
            String severity = vuln.getSeverity() != null ? vuln.getSeverity().toUpperCase() : "MEDIUM";
            double penalty = switch (severity) {
                case "CRITICAL" -> 40.0;
                case "HIGH" -> 20.0;
                case "MEDIUM" -> 10.0;
                case "LOW" -> 3.0;
                default -> 5.0;
            };
            score -= penalty;
        }

        return Math.max(0.0, score);
    }

    private double calculateFreshnessScore(DependencyRecord dependency) {
        if (dependency.getVersion() == null || dependency.getLatestVersion() == null) {
            return 70.0;
        }

        int comparison = dependencyParserService.compareVersions(dependency.getVersion(), dependency.getLatestVersion());
        if (comparison >= 0) {
            return 100.0;
        }

        String[] currentParts = dependency.getVersion().replace("-SNAPSHOT", "").split("\\.");
        String[] latestParts = dependency.getLatestVersion().replace("-SNAPSHOT", "").split("\\.");

        int currentMajor = parseSafe(currentParts, 0);
        int currentMinor = parseSafe(currentParts, 1);
        int currentPatch = parseSafe(currentParts, 2);
        int latestMajor = parseSafe(latestParts, 0);
        int latestMinor = parseSafe(latestParts, 1);
        int latestPatch = parseSafe(latestParts, 2);

        int majorDiff = latestMajor - currentMajor;
        int minorDiff = latestMinor - currentMinor;
        int patchDiff = latestPatch - currentPatch;

        double score = 100.0;

        if (majorDiff > 0) {
            score -= 30 * Math.min(majorDiff, 3);
            if (majorDiff >= 2) score -= 10;
        } else if (minorDiff > 0) {
            score -= 10 * Math.min(minorDiff, 5);
        } else if (patchDiff > 0) {
            score -= 2 * Math.min(patchDiff, 10);
        }

        double agePenalty = calculateAgePenalty(dependency);
        score -= agePenalty;

        return Math.max(0.0, score);
    }

    private double calculateAgePenalty(DependencyRecord dependency) {
        int releaseAgeMonths = getReleaseAgeMonths(dependency.getGroupId(), dependency.getArtifactId(), dependency.getVersion());

        if (releaseAgeMonths <= 3) return 0;
        if (releaseAgeMonths <= 6) return 5;
        if (releaseAgeMonths <= 12) return 10;
        if (releaseAgeMonths <= 24) return 20;
        return Math.min(30, releaseAgeMonths);
    }

    private int getReleaseAgeMonths(String groupId, String artifactId, String version) {
        Map<String, LocalDate> knownDates = getKnownReleaseDates();
        String key = groupId + ":" + artifactId + ":" + version;

        LocalDate releaseDate = knownDates.getOrDefault(key, LocalDate.now().minusMonths(6));
        return (int) ChronoUnit.MONTHS.between(releaseDate, LocalDate.now());
    }

    private Map<String, LocalDate> getKnownReleaseDates() {
        Map<String, LocalDate> dates = new HashMap<>();
        dates.put("org.springframework.boot:spring-boot-starter-web:2.7.0", LocalDate.of(2022, 5, 19));
        dates.put("org.springframework.boot:spring-boot-starter-web:2.7.18", LocalDate.of(2023, 11, 23));
        dates.put("org.springframework.boot:spring-boot-starter-web:3.0.0", LocalDate.of(2022, 11, 24));
        dates.put("org.springframework.boot:spring-boot-starter-web:3.2.0", LocalDate.of(2023, 11, 23));
        dates.put("org.springframework.boot:spring-boot-starter-web:3.2.5", LocalDate.of(2024, 4, 18));
        dates.put("org.springframework:spring-core:5.3.20", LocalDate.of(2022, 5, 11));
        dates.put("org.springframework:spring-core:6.0.0", LocalDate.of(2022, 11, 16));
        dates.put("org.springframework:spring-core:6.1.0", LocalDate.of(2023, 11, 16));
        dates.put("com.fasterxml.jackson.core:jackson-databind:2.13.0", LocalDate.of(2021, 9, 12));
        dates.put("com.fasterxml.jackson.core:jackson-databind:2.15.0", LocalDate.of(2023, 4, 23));
        dates.put("com.fasterxml.jackson.core:jackson-databind:2.17.0", LocalDate.of(2024, 3, 12));
        dates.put("org.apache.commons:commons-lang3:3.12.0", LocalDate.of(2022, 10, 12));
        dates.put("org.apache.commons:commons-lang3:3.14.0", LocalDate.of(2024, 1, 2));
        dates.put("org.slf4j:slf4j-api:1.7.36", LocalDate.of(2022, 2, 8));
        dates.put("org.slf4j:slf4j-api:2.0.0", LocalDate.of(2022, 8, 19));
        dates.put("org.slf4j:slf4j-api:2.0.13", LocalDate.of(2024, 3, 13));
        dates.put("mysql:mysql-connector-java:8.0.28", LocalDate.of(2022, 1, 18));
        dates.put("mysql:mysql-connector-java:8.0.33", LocalDate.of(2023, 4, 25));
        return dates;
    }

    private double calculatePopularityScore(DependencyRecord dependency) {
        String key = dependency.getGroupId() + ":" + dependency.getArtifactId();
        return POPULARITY_CACHE.computeIfAbsent(key, k -> estimatePopularity(dependency.getGroupId(), dependency.getArtifactId()));
    }

    private double estimatePopularity(String groupId, String artifactId) {
        Map<String, Double> knownPopularity = getKnownPopularity();
        String key = groupId + ":" + artifactId;

        Double known = knownPopularity.get(key);
        if (known != null) {
            return known;
        }

        if (groupId.startsWith("org.springframework")) {
            return 95.0;
        }
        if (groupId.startsWith("com.fasterxml.jackson")) {
            return 90.0;
        }
        if (groupId.startsWith("org.apache.commons")) {
            return 85.0;
        }
        if (groupId.startsWith("org.slf4j")) {
            return 92.0;
        }
        if (groupId.startsWith("org.junit") || groupId.startsWith("org.mockito")) {
            return 88.0;
        }
        if (groupId.startsWith("com.google.guava")) {
            return 87.0;
        }

        return 70.0;
    }

    private Map<String, Double> getKnownPopularity() {
        Map<String, Double> popularity = new HashMap<>();
        popularity.put("org.springframework.boot:spring-boot-starter-web", 98.0);
        popularity.put("org.springframework.boot:spring-boot-starter-data-jpa", 96.0);
        popularity.put("org.springframework.boot:spring-boot-starter-security", 94.0);
        popularity.put("org.springframework.boot:spring-boot-starter-test", 97.0);
        popularity.put("org.springframework:spring-core", 99.0);
        popularity.put("org.springframework:spring-context", 98.0);
        popularity.put("org.springframework:spring-web", 97.0);
        popularity.put("com.fasterxml.jackson.core:jackson-databind", 97.0);
        popularity.put("com.fasterxml.jackson.core:jackson-core", 96.0);
        popularity.put("com.fasterxml.jackson.core:jackson-annotations", 95.0);
        popularity.put("org.apache.commons:commons-lang3", 92.0);
        popularity.put("org.apache.commons:commons-collections4", 85.0);
        popularity.put("org.slf4j:slf4j-api", 99.0);
        popularity.put("ch.qos.logback:logback-classic", 95.0);
        popularity.put("mysql:mysql-connector-java", 90.0);
        popularity.put("org.postgresql:postgresql", 88.0);
        popularity.put("com.h2database:h2", 82.0);
        popularity.put("org.projectlombok:lombok", 93.0);
        popularity.put("org.junit.jupiter:junit-jupiter-api", 95.0);
        popularity.put("org.mockito:mockito-core", 92.0);
        popularity.put("com.google.guava:guava", 90.0);
        popularity.put("org.apache.httpcomponents.client5:httpclient5", 85.0);
        popularity.put("io.jsonwebtoken:jjwt-api", 80.0);
        return popularity;
    }

    private String getGrade(double score) {
        if (score >= 90) return "A+";
        if (score >= 85) return "A";
        if (score >= 80) return "A-";
        if (score >= 75) return "B+";
        if (score >= 70) return "B";
        if (score >= 65) return "B-";
        if (score >= 60) return "C+";
        if (score >= 55) return "C";
        if (score >= 50) return "C-";
        if (score >= 40) return "D";
        return "F";
    }

    private List<String> generateRecommendations(DependencyRecord dependency,
                                                 double vulnerabilityScore,
                                                 double freshnessScore,
                                                 double popularityScore) {
        List<String> recommendations = new ArrayList<>();

        if (vulnerabilityScore < 70) {
            recommendations.add("存在高危安全漏洞，建议立即升级到最新安全版本");
        } else if (vulnerabilityScore < 90) {
            recommendations.add("存在中低危安全漏洞，建议尽快升级");
        }

        if (freshnessScore < 60) {
            recommendations.add("版本过旧，存在兼容性和安全性风险，建议升级");
        } else if (freshnessScore < 80) {
            recommendations.add("版本落后较多，建议关注并计划升级");
        }

        if (popularityScore < 60) {
            recommendations.add("该依赖流行度较低，建议评估维护状态和替代方案");
        } else if (popularityScore < 75) {
            recommendations.add("该依赖社区活跃度一般，建议关注维护状态");
        }

        if (Boolean.TRUE.equals(dependency.getIsOutdated()) && dependency.getLatestVersion() != null) {
            recommendations.add("最新版本可用: " + dependency.getLatestVersion());
        }

        if (recommendations.isEmpty()) {
            recommendations.add("该依赖状态良好，无需特殊处理");
        }

        return recommendations;
    }

    private int parseSafe(String[] parts, int index) {
        if (index < parts.length) {
            try {
                return Integer.parseInt(parts[index].replaceAll("[^0-9].*", ""));
            } catch (NumberFormatException e) {
                return 0;
            }
        }
        return 0;
    }

    public Map<String, Object> getProjectHealthSummary(List<DependencyRecord> dependencies) {
        if (dependencies.isEmpty()) {
            return Map.of(
                    "overallScore", 0.0,
                    "grade", "N/A",
                    "healthyCount", 0,
                    "warningCount", 0,
                    "criticalCount", 0,
                    "averageVulnerabilityScore", 0.0,
                    "averageFreshnessScore", 0.0,
                    "averagePopularityScore", 0.0
            );
        }

        double totalScore = 0;
        double totalVuln = 0;
        double totalFresh = 0;
        double totalPop = 0;
        int healthy = 0;
        int warning = 0;
        int critical = 0;

        for (DependencyRecord dep : dependencies) {
            HealthScore score = calculateHealthScore(dep);
            totalScore += score.getOverallScore();
            totalVuln += score.getVulnerabilityScore();
            totalFresh += score.getFreshnessScore();
            totalPop += score.getPopularityScore();

            if (score.getOverallScore() >= 80) {
                healthy++;
            } else if (score.getOverallScore() >= 60) {
                warning++;
            } else {
                critical++;
            }
        }

        int n = dependencies.size();
        double overall = totalScore / n;
        String grade = getGrade(overall);

        return Map.of(
                "overallScore", Math.round(overall * 100.0) / 100.0,
                "grade", grade,
                "healthyCount", healthy,
                "warningCount", warning,
                "criticalCount", critical,
                "averageVulnerabilityScore", Math.round((totalVuln / n) * 100.0) / 100.0,
                "averageFreshnessScore", Math.round((totalFresh / n) * 100.0) / 100.0,
                "averagePopularityScore", Math.round((totalPop / n) * 100.0) / 100.0
        );
    }

    @lombok.Data
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class HealthScore {
        private String dependencyKey;
        private double overallScore;
        private String grade;
        private double vulnerabilityScore;
        private double freshnessScore;
        private double popularityScore;
        private List<String> recommendations;
    }
}
