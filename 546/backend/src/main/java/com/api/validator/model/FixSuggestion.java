package com.api.validator.model;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class FixSuggestion {

    private String field;
    private FixType fixType;
    private Severity severity;
    private String description;
    private String originalValue;
    private String suggestedFix;
    private String codeSnippet;
    private List<String> alternatives = new ArrayList<>();

    public enum FixType {
        ADD_MISSING_FIELD,
        FIX_TYPE_MISMATCH,
        FIX_FORMAT,
        FIX_VALUE_RANGE,
        REMOVE_EXTRA_FIELD,
        FIX_STRUCTURE,
        FIX_ENUM_VALUE
    }

    public enum Severity {
        CRITICAL,
        HIGH,
        MEDIUM,
        LOW
    }

    public void addAlternative(String alternative) {
        this.alternatives.add(alternative);
    }
}
