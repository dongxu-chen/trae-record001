package com.apiversion.compare.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("routing_rule")
@Schema(description = "路由规则")
public class RoutingRule {

    @TableId(type = IdType.AUTO)
    @Schema(description = "规则ID")
    private Long id;

    @Schema(description = "版本ID")
    private Long versionId;

    @Schema(description = "规则类型：HEADER, COOKIE, QUERY, IP")
    private String ruleType;

    @Schema(description = "规则键")
    private String ruleKey;

    @Schema(description = "规则值")
    private String ruleValue;

    @Schema(description = "匹配方式：EQUAL, CONTAIN, REGEX")
    private String matchMode;

    @Schema(description = "优先级")
    private Integer priority;

    @Schema(description = "是否启用")
    private Boolean enabled;

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
