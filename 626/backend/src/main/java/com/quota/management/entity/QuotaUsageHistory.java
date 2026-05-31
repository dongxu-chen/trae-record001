package com.quota.management.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuotaUsageHistory implements Serializable {

    private static final long serialVersionUID = 1L;

    private String tenantId;

    private String granularity;

    private long timestamp;

    private LocalDateTime dateTime;

    private long used;

    private long limit;

    private double usageRate;
}
