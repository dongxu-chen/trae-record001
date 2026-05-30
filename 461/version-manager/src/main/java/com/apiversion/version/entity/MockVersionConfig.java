package com.apiversion.version.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("mock_version_config")
@Schema(description = "Mock版本配置")
public class MockVersionConfig {

    @TableId(type = IdType.AUTO)
    @Schema(description = "配置ID")
    private Long id;

    @Schema(description = "版本ID")
    private Long versionId;

    @Schema(description = "接口路径")
    private String path;

    @Schema(description = "HTTP方法")
    private String method;

    @Schema(description = "Mock类型: SUCCESS-成功响应, DELAY-延迟响应, ERROR-错误响应, CUSTOM-自定义响应")
    private String mockType;

    @Schema(description = "模拟延迟(ms)")
    private Integer delayMs;

    @Schema(description = "模拟错误码")
    private Integer errorCode;

    @Schema(description = "模拟错误信息")
    private String errorMessage;

    @Schema(description = "自定义响应JSON")
    private String customResponse;

    @Schema(description = "是否启用")
    private Boolean enabled;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
