package com.apiversion.version.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@TableName("routing_rule")
@Schema(description = "路由规则")
public class RoutingRule {

    @TableId(type = IdType.AUTO)
    @Schema(description = "规则ID")
    private Long id;

    @Schema(description = "API名称")
    private String apiName;

    @Schema(description = "版本ID")
    private Long versionId;

    @Schema(description = "规则类型：PATH, HEADER, QUERY, WEIGHTED")
    private String ruleType;

    @Schema(description = "规则键")
    private String ruleKey;

    @Schema(description = "规则值")
    private String ruleValue;

    @Schema(description = "匹配方式：EQUAL, CONTAIN, REGEX")
    private String matchMode;

    @Schema(description = "v1权重")
    private Integer weightV1;

    @Schema(description = "v2权重")
    private Integer weightV2;

    @Schema(description = "优先级")
    private Integer priority;

    @Schema(description = "是否启用")
    private Boolean enabled;

    @Schema(description = "Header解析规则JSON")
    @TableField(exist = false)
    private List<HeaderParseRule> headerParseRules;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @Schema(description = "是否删除")
    @TableLogic
    private Integer deleted;

    @Data
    @Schema(description = "Header解析规则")
    public static class HeaderParseRule {
        @Schema(description = "Header名称")
        private String headerName;

        @Schema(description = "解析策略：DIRECT, REGEX, PREFIX, DELIMITER, SEMVER")
        private String parseStrategy;

        @Schema(description = "匹配模式（正则、前缀、分隔符等）")
        private String pattern;

        @Schema(description = "默认值")
        private String defaultValue;

        @Schema(description = "优先级，数字越小优先级越高")
        private Integer priority;
    }
}
