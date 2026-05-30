package com.apiversion.compare.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "差异项")
public class DiffItem {

    @Schema(description = "差异类型：ENDPOINT-接口, PARAM-参数, RESPONSE-响应, SCHEMA-模型")
    private String diffType;

    @Schema(description = "变更类型：ADD-新增, DELETE-删除, MODIFY-修改")
    private String changeType;

    @Schema(description = "变更路径，如：GET /api/users/{id}")
    private String changePath;

    @Schema(description = "变更前内容")
    private String oldValue;

    @Schema(description = "变更后内容")
    private String newValue;

    @Schema(description = "是否为破坏性变更")
    private Boolean breakingChange;

    @Schema(description = "变更描述")
    private String description;
}
