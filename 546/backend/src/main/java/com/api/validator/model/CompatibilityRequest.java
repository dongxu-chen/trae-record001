package com.api.validator.model;

import lombok.Data;

@Data
public class CompatibilityRequest {

    private String oldOpenApiSpec;
    private String newOpenApiSpec;
    private String oldVersion;
    private String newVersion;
    private String path;
    private String method;
    private Integer statusCode;
}
