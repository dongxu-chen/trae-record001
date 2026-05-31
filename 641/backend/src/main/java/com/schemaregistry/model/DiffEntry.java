package com.schemaregistry.model;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DiffEntry {
    private String path;
    private String field;
    private String oldValue;
    private String newValue;
    private String description;
    private DiffType type;
    private boolean hasDefault;
    private String oldFieldName;
    private String newFieldName;
    private double renameConfidence;
    private Integer level;

    public enum DiffType {
        FIELD_ADDED,
        FIELD_REMOVED,
        FIELD_RENAMED,
        TYPE_CHANGED,
        DEFAULT_CHANGED,
        REQUIRED_CHANGED,
        DOC_CHANGED
    }
}
