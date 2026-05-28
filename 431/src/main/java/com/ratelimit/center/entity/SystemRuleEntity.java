package com.ratelimit.center.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("system_rule")
public class SystemRuleEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String serviceName;

    private Integer grade;

    private Double count;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    private String remark;
}
