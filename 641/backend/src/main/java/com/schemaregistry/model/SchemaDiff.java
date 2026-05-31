package com.schemaregistry.model;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SchemaDiff {
    private String oldVersion;
    private String newVersion;
    private List<DiffEntry> additions;
    private List<DiffEntry> deletions;
    private List<DiffEntry> modifications;
    private List<DiffEntry> renames;
    private List<StructuredDiffNode> structuredDiff;
}
