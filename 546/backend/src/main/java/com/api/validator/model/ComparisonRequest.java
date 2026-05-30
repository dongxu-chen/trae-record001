package com.api.validator.model;

import lombok.Data;

@Data
public class ComparisonRequest {

    private String openApiSpec;
    private String path;
    private String method;
    private Integer statusCode;
    private String env1Name;
    private String env2Name;
    private String env1ResponseBody;
    private String env2ResponseBody;
}
