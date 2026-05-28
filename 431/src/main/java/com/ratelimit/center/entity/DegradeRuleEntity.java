package com.ratelimit.center.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("degrade_rule")
public class DegradeRuleEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String serviceName;

    private String resource;

    private Integer grade;

    private Double count;

    private Integer timeWindow;

    private Integer minRequestAmount;

    private Integer slowRatioThreshold;

    private Integer statIntervalMs;

    private String limitApp;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    private String remark;
}
