package com.api.validator.model;

import lombok.Data;

import java.util.List;

@Data
public class FixRequest {

    private String openApiSpec;
    private String path;
    private String method;
    private Integer statusCode;
    private String responseBody;
    private boolean autoFix;
}
