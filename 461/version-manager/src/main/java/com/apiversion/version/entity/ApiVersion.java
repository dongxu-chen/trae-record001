package com.apiversion.version.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("api_version")
@Schema(description = "API版本")
public class ApiVersion {

    @TableId(type = IdType.AUTO)
    @Schema(description = "版本ID")
    private Long id;

    @Schema(description = "服务名称")
    private String serviceName;

    @Schema(description = "版本号")
    private String version;

    @Schema(description = "版本描述")
    private String description;

    @Schema(description = "状态：DRAFT-草稿, PUBLISHED-已发布, DEPRECATED-已废弃, OFFLINE-已下线")
    private String status;

    @Schema(description = "是否默认版本")
    private Boolean isDefault;

    @Schema(description = "发布时间")
    private LocalDateTime publishTime;

    @Schema(description = "废弃时间")
    private LocalDateTime deprecateTime;

    @Schema(description = "下线时间")
    private LocalDateTime offlineTime;

    @Schema(description = "计划下线时间")
    private LocalDateTime plannedRetireTime;

    @Schema(description = "废弃提示信息")
    private String deprecationMessage;

    @Schema(description = "是否为Mock版本")
    private Boolean isMock;

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
