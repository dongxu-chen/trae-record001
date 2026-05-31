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
public class TenantQuota implements Serializable {

    private static final long serialVersionUID = 1L;

    private String tenantId;

    private String tenantName;

    private Long minuteLimit;

    private Long hourLimit;

    private Long dayLimit;

    private OverLimitStrategy overLimitStrategy;

    private Double warningThreshold;

    private String notificationEmail;

    private Boolean enabled;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    public enum OverLimitStrategy {
        REJECT,
        DOWNGRADE,
        QUEUE
    }
}
