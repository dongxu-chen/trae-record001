package com.ratelimit.center.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("param_flow_rule")
public class ParamFlowRuleEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String serviceName;

    private String resource;

    private Integer grade;

    private Integer paramIdx;

    private Double count;

    private Integer paramFlowItem;

    private String paramHotItems;

    private Integer burstCount;

    private Long durationInSec;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    private String remark;
}
