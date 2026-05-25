package com.mfa.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuthMethodStats {
    private String method;
    private String methodName;
    private Long totalAttempts;
    private Long successCount;
    private Long failureCount;
    private BigDecimal successRate;
    private BigDecimal usagePercentage;
    private Long avgResponseTimeMs;
}
