package com.ratelimit.center.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("flow_rule")
public class FlowRuleEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String serviceName;

    private String resource;

    private Integer grade;

    private Double count;

    private Integer strategy;

    private String refResource;

    private Integer controlBehavior;

    private Integer warmUpPeriodSec;

    private Integer maxQueueingTimeMs;

    private Boolean clusterMode;

    private Boolean clusterFallback;

    private Integer clusterThresholdType;

    private Integer clusterThresholdConfig;

    private Integer paramFlowItem;

    private String paramHotItems;

    private String limitApp;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    private String remark;
}
