package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("domain_rate_limit")
public class DomainRateLimit extends BaseEntity {
    private String domain;
    private Integer limitPerMinute;
    private Integer status;
}
