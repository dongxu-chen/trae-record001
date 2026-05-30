package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RateLimitRecommendation {
    private String serviceId;
    private RateLimitRule recommendedServiceRule;
    private Map<String, RateLimitRule> recommendedApiRules;
    private List<String> reasoning;
    private double riskScore;
    private LocalDateTime generateTime;
    private TrafficPrediction prediction;
}
