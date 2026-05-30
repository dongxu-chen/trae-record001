package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RateLimitRule {
    private int qpsThreshold;
    private int burstCapacity;
    private int warmUpPeriodSec;
    private int maxWaitTimeMs;
    private String limitType;
    private String fallbackStrategy;
    private double confidenceScore;
}
