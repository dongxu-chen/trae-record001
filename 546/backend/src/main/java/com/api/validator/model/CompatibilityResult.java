package com.api.validator.model;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class CompatibilityResult {

    private String oldVersion;
    private String newVersion;
    private String path;
    private String method;
    private boolean compatible;
    private CompatibilityLevel compatibilityLevel;
    private List<CompatibilityIssue> issues = new ArrayList<>();
    private List<String> suggestions = new ArrayList<>();

    public enum CompatibilityLevel {
        FULLY_COMPATIBLE,
        BACKWARD_COMPATIBLE,
        PARTIALLY_COMPATIBLE,
        BREAKING_CHANGE
    }

    @Data
    public static class CompatibilityIssue {
        private String field;
        private IssueType issueType;
        private Severity severity;
        private String description;
        private String oldDefinition;
        private String newDefinition;

        public CompatibilityIssue(String field, IssueType issueType, Severity severity,
                                  String description, String oldDefinition, String newDefinition) {
            this.field = field;
            this.issueType = issueType;
            this.severity = severity;
            this.description = description;
            this.oldDefinition = oldDefinition;
            this.newDefinition = newDefinition;
        }
    }

    public enum IssueType {
        FIELD_REMOVED,
        FIELD_TYPE_CHANGED,
        REQUIRED_FIELD_ADDED,
        FIELD_RESTRICTED,
        ENUM_VALUE_REMOVED,
        FORMAT_CHANGED,
        RANGE_NARROWED,
        FIELD_ADDED_OPTIONAL,
        FIELD_WIDENED,
        ENUM_VALUE_ADDED,
        RANGE_WIDENED
    }

    public enum Severity {
        BREAKING,
        WARNING,
        INFO
    }

    public void addIssue(CompatibilityIssue issue) {
        this.issues.add(issue);
    }

    public void addSuggestion(String suggestion) {
        this.suggestions.add(suggestion);
    }
}
