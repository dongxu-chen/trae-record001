package com.quota.management.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Set;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QuotaPool implements Serializable {

    private static final long serialVersionUID = 1L;

    public enum AllocationStrategy {
        EQUAL,
        WEIGHTED,
        DEMAND_BASED,
        FAIR_QUEUE
    }

    private String poolId;

    private String poolName;

    private String description;

    private Long minuteCapacity;

    private Long hourCapacity;

    private Long dayCapacity;

    private Set<String> memberTenants;

    private AllocationStrategy allocationStrategy;

    private Long maxPerMemberMinute;

    private Long maxPerMemberHour;

    private Long maxPerMemberDay;

    private Boolean enabled;

    private String createdBy;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}
