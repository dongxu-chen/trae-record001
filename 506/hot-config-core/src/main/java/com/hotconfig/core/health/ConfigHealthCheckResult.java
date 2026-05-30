package com.hotconfig.core.health;

import java.time.Instant;
import java.util.*;

public class ConfigHealthCheckResult {

    private final Instant timestamp;
    private final HealthStatus overallStatus;
    private final Map<String, HealthIssue> issues;
    private final Map<String, Object> metrics;
    private final String checkName;

    public ConfigHealthCheckResult(String checkName, HealthStatus overallStatus) {
        this.checkName = checkName;
        this.timestamp = Instant.now();
        this.overallStatus = overallStatus;
        this.issues = new LinkedHashMap<>();
        this.metrics = new LinkedHashMap<>();
    }

    public enum HealthStatus {
        HEALTHY,
        WARNING,
        CRITICAL,
        UNKNOWN
    }

    public enum IssueSeverity {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }

    public enum IssueType {
        DANGLING_REFERENCE,
        MISSING_REQUIRED,
        TYPE_MISMATCH,
        INVALID_VALUE,
        DUPLICATE_KEY,
        CIRCULAR_REFERENCE,
        UNUSED_CONFIG,
        DEPRECATED_KEY,
        FORMAT_ERROR,
        OTHER
    }

    public static class HealthIssue {
        private final String key;
        private final IssueType type;
        private final IssueSeverity severity;
        private final String message;
        private final String details;
        private final String suggestion;

        public HealthIssue(String key, IssueType type, IssueSeverity severity,
                           String message, String details, String suggestion) {
            this.key = key;
            this.type = type;
            this.severity = severity;
            this.message = message;
            this.details = details;
            this.suggestion = suggestion;
        }

        public String getKey() {
            return key;
        }

        public IssueType getType() {
            return type;
        }

        public IssueSeverity getSeverity() {
            return severity;
        }

        public String getMessage() {
            return message;
        }

        public String getDetails() {
            return details;
        }

        public String getSuggestion() {
            return suggestion;
        }

        @Override
        public String toString() {
            return String.format("[%s] %s: %s (key: %s)", severity, type, message, key);
        }
    }

    public void addIssue(HealthIssue issue) {
        issues.put(issue.getKey() + "-" + issue.getType(), issue);
    }

    public void addIssue(String key, IssueType type, IssueSeverity severity,
                         String message, String details, String suggestion) {
        addIssue(new HealthIssue(key, type, severity, message, details, suggestion));
    }

    public void addMetric(String name, Object value) {
        metrics.put(name, value);
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public HealthStatus getOverallStatus() {
        return overallStatus;
    }

    public Map<String, HealthIssue> getIssues() {
        return Collections.unmodifiableMap(issues);
    }

    public List<HealthIssue> getIssuesBySeverity(IssueSeverity severity) {
        List<HealthIssue> result = new ArrayList<>();
        for (HealthIssue issue : issues.values()) {
            if (issue.getSeverity() == severity) {
                result.add(issue);
            }
        }
        return result;
    }

    public List<HealthIssue> getIssuesByType(IssueType type) {
        List<HealthIssue> result = new ArrayList<>();
        for (HealthIssue issue : issues.values()) {
            if (issue.getType() == type) {
                result.add(issue);
            }
        }
        return result;
    }

    public Map<String, Object> getMetrics() {
        return Collections.unmodifiableMap(metrics);
    }

    public String getCheckName() {
        return checkName;
    }

    public int getIssueCount() {
        return issues.size();
    }

    public int getIssueCountBySeverity(IssueSeverity severity) {
        return (int) issues.values().stream()
                .filter(i -> i.getSeverity() == severity)
                .count();
    }

    public boolean isHealthy() {
        return overallStatus == HealthStatus.HEALTHY;
    }

    public boolean hasCriticalIssues() {
        return getIssueCountBySeverity(IssueSeverity.CRITICAL) > 0;
    }

    public boolean hasHighIssues() {
        return getIssueCountBySeverity(IssueSeverity.HIGH) > 0;
    }

    public String getSummary() {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("=== Config Health Check: %s ===\n", checkName));
        sb.append(String.format("Timestamp: %s\n", timestamp));
        sb.append(String.format("Overall Status: %s\n", overallStatus));
        sb.append(String.format("Total Issues: %d\n", issues.size()));

        for (IssueSeverity severity : IssueSeverity.values()) {
            int count = getIssueCountBySeverity(severity);
            if (count > 0) {
                sb.append(String.format("  %s: %d\n", severity, count));
            }
        }

        if (!issues.isEmpty()) {
            sb.append("\nIssues:\n");
            for (HealthIssue issue : issues.values()) {
                sb.append(String.format("  - [%s] %s: %s\n", issue.getSeverity(), issue.getType(), issue.getMessage()));
                if (issue.getDetails() != null) {
                    sb.append(String.format("    Details: %s\n", issue.getDetails()));
                }
                if (issue.getSuggestion() != null) {
                    sb.append(String.format("    Suggestion: %s\n", issue.getSuggestion()));
                }
            }
        }

        if (!metrics.isEmpty()) {
            sb.append("\nMetrics:\n");
            for (Map.Entry<String, Object> entry : metrics.entrySet()) {
                sb.append(String.format("  %s: %s\n", entry.getKey(), entry.getValue()));
            }
        }

        return sb.toString();
    }

    @Override
    public String toString() {
        return "ConfigHealthCheckResult{" +
                "checkName='" + checkName + '\'' +
                ", timestamp=" + timestamp +
                ", overallStatus=" + overallStatus +
                ", issueCount=" + issues.size() +
                '}';
    }
}
