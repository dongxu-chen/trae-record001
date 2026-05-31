package com.schemaregistry.model;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class GeneratedCode {
    private String language;
    private String fileName;
    private String code;
    private String packageName;
    private String className;
}
