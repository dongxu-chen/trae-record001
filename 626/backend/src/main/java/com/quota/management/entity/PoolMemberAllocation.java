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
public class PoolMemberAllocation implements Serializable {

    private static final long serialVersionUID = 1L;

    private String poolId;

    private String tenantId;

    private Long minuteAllocated;

    private Long hourAllocated;

    private Long dayAllocated;

    private Long minuteUsed;

    private Long hourUsed;

    private Long dayUsed;

    private Double weight;

    private Long priority;

    private Long lastAllocatedAt;
}
