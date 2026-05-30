package com.apiversion.version.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("api_endpoint")
@Schema(description = "API端点")
public class ApiEndpoint {

    @TableId(type = IdType.AUTO)
    @Schema(description = "端点ID")
    private Long id;

    @Schema(description = "版本ID")
    private Long versionId;

    @Schema(description = "HTTP方法")
    private String httpMethod;

    @Schema(description = "API路径")
    private String apiPath;

    @Schema(description = "请求参数定义")
    private String requestParams;

    @Schema(description = "响应参数定义")
    private String responseParams;

    @Schema(description = "请求示例")
    private String requestExample;

    @Schema(description = "响应示例")
    private String responseExample;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @Schema(description = "是否删除")
    @TableLogic
    private Integer deleted;
}
