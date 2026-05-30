package com.api.validator.model;

import lombok.Data;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Data
public class ValidationResult {

    private boolean valid;
    private List<ValidationError> errors = new ArrayList<>();
    private String path;
    private String method;
    private Integer statusCode;

    public void addError(String field, String message, ErrorType type) {
        this.errors.add(new ValidationError(field, message, type, getDefaultSeverity(type)));
    }

    public void addError(String field, String message, ErrorType type, Severity severity) {
        this.errors.add(new ValidationError(field, message, type, severity));
    }

    public void sortErrorsBySeverity() {
        if (this.errors == null || this.errors.isEmpty()) {
            return;
        }

        this.errors.sort(Comparator
            .comparingInt((ValidationError e) -> getSeverityOrder(e.getSeverity()))
            .reversed()
            .thenComparing(ValidationError::getField));
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

    private Severity getDefaultSeverity(ErrorType type) {
        switch (type) {
            case REQUIRED_FIELD_MISSING:
                return Severity.CRITICAL;
            case TYPE_MISMATCH:
                return Severity.HIGH;
            case STRUCTURE_INVALID:
            case SCHEMA_ERROR:
                return Severity.HIGH;
            case FORMAT_INVALID:
            case UNKNOWN_FIELD:
                return Severity.MEDIUM;
            default:
                return Severity.LOW;
        }
    }

    public enum ErrorType {
        REQUIRED_FIELD_MISSING,
        TYPE_MISMATCH,
        FORMAT_INVALID,
        STRUCTURE_INVALID,
        UNKNOWN_FIELD,
        SCHEMA_ERROR
    }

    public enum Severity {
        CRITICAL,
        HIGH,
        MEDIUM,
        LOW
    }

    @Data
    public static class ValidationError {
        private String field;
        private String message;
        private ErrorType type;
        private Severity severity;

        public ValidationError(String field, String message, ErrorType type) {
            this.field = field;
            this.message = message;
            this.type = type;
            this.severity = Severity.MEDIUM;
        }

        public ValidationError(String field, String message, ErrorType type, Severity severity) {
            this.field = field;
            this.message = message;
            this.type = type;
            this.severity = severity;
        }
    }
}
