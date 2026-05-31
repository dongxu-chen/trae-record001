package com.quota.management.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuotaUsage implements Serializable {

    private static final long serialVersionUID = 1L;

    private String tenantId;

    private Long minuteUsed;

    private Long hourUsed;

    private Long dayUsed;

    private Long minuteRemaining;

    private Long hourRemaining;

    private Long dayRemaining;

    private Double minuteUsageRate;

    private Double hourUsageRate;

    private Double dayUsageRate;

    private Boolean warningTriggered;

    private String warningLevel;
}
