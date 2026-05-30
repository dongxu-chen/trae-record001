package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RateLimitConfig {
    private String serviceId;
    private RateLimitRule serviceLevelRule;
    private Map<String, RateLimitRule> apiLevelRules;
    private boolean enabled;
    private String strategy;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
