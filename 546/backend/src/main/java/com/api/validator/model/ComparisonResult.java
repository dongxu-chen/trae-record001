package com.api.validator.model;

import lombok.Data;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Data
public class ComparisonResult {

    private String path;
    private String method;
    private String env1Name;
    private String env2Name;
    private List<Difference> differences = new ArrayList<>();
    private boolean hasDifferences;
    private ValidationResult env1Validation;
    private ValidationResult env2Validation;

    public enum Severity {
        CRITICAL,
        HIGH,
        MEDIUM,
        LOW
    }

    @Data
    public static class Difference {
        private String field;
        private DifferenceType type;
        private Severity severity;
        private Object env1Value;
        private Object env2Value;
        private String description;

        public Difference(String field, DifferenceType type, Object env1Value, Object env2Value, String description) {
            this.field = field;
            this.type = type;
            this.severity = getDefaultSeverity(type);
            this.env1Value = env1Value;
            this.env2Value = env2Value;
            this.description = description;
        }

        public Difference(String field, DifferenceType type, Severity severity, Object env1Value, Object env2Value, String description) {
            this.field = field;
            this.type = type;
            this.severity = severity;
            this.env1Value = env1Value;
            this.env2Value = env2Value;
            this.description = description;
        }

        private Severity getDefaultSeverity(DifferenceType type) {
            switch (type) {
                case FIELD_REMOVED:
                    return Severity.CRITICAL;
                case TYPE_CHANGED:
                case STRUCTURE_MISMATCH:
                    return Severity.HIGH;
                case FIELD_ADDED:
                case ARRAY_LENGTH_CHANGED:
                    return Severity.MEDIUM;
                case VALUE_CHANGED:
                    return Severity.LOW;
                default:
                    return Severity.LOW;
            }
        }
    }

    public enum DifferenceType {
        VALUE_CHANGED,
        FIELD_ADDED,
        FIELD_REMOVED,
        TYPE_CHANGED,
        ARRAY_LENGTH_CHANGED,
        STRUCTURE_MISMATCH
    }

    public void addDifference(Difference difference) {
        this.differences.add(difference);
        this.hasDifferences = true;
    }

    public void sortDifferencesBySeverity() {
        if (this.differences == null || this.differences.isEmpty()) {
            return;
        }

        this.differences.sort(Comparator
            .comparingInt((Difference d) -> getSeverityOrder(d.getSeverity()))
            .reversed()
            .thenComparing(Difference::getField));
    }

    private int getSeverityOrder(Severity severity) {
        if (severity == null) return 0;
        switch (severity) {
            case CRITICAL: return 4;
            case HIGH: return 3;
            case MEDIUM: return 2;
            case LOW: return 1;
            default: return 0;
        }
    }
}
