package com.api.validator.model;

import lombok.Data;

@Data
public class ValidationRequest {

    private String openApiSpec;
    private String path;
    private String method;
    private Integer statusCode;
    private String responseBody;
}
