package com.ratelimit.center.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("rate_limit_log")
public class RateLimitLogEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String serviceName;

    private String resource;

    private String origin;

    private String ruleType;

    private Integer passCount;

    private Integer blockCount;

    private Long rt;

    private String exception;

    private String clientIp;

    private String requestPath;

    private String requestMethod;

    private String requestParams;

    private LocalDateTime occurTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
