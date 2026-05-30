package com.apiversion.compare.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "差异对比请求")
public class DiffRequest {

    @Schema(description = "源版本OpenAPI文档JSON")
    private String sourceOpenApi;

    @Schema(description = "目标版本OpenAPI文档JSON")
    private String targetOpenApi;

    @Schema(description = "源版本ID")
    private Long sourceVersionId;

    @Schema(description = "目标版本ID")
    private Long targetVersionId;
}
