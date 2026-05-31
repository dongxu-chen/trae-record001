package com.schemaregistry.model;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.util.ArrayList;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StructuredDiffNode {
    private String path;
    private String fieldName;
    private String oldType;
    private String newType;
    private String oldDefault;
    private String newDefault;
    private Boolean oldRequired;
    private Boolean newRequired;
    private ChangeType changeType;
    private Integer level;
    private boolean hasDefault;
    private String renameFrom;
    private String renameTo;
    private double renameConfidence;
    private List<StructuredDiffNode> children = new ArrayList<>();

    public enum ChangeType {
        UNCHANGED,
        ADDED,
        REMOVED,
        MODIFIED,
        RENAMED
    }
}
