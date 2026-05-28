package com.ratelimit.center.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("authority_rule")
public class AuthorityRuleEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String serviceName;

    private String resource;

    private String limitApp;

    private Integer strategy;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    private String remark;
}
