package com.apiversion.version.entity;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("header_parse_rule")
@Schema(description = "Header解析规则")
public class HeaderParseRule {

    @TableId(type = IdType.AUTO)
    @Schema(description = "规则ID")
    private Long id;

    @Schema(description = "关联的路由规则ID")
    private Long routingRuleId;

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
