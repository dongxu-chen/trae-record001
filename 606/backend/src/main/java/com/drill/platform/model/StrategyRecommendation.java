package com.drill.platform.model;

import lombok.Data;
import java.util.Date;
import java.util.List;
import java.util.Map;

@Data
public class StrategyRecommendation {
    private String id;
    private String targetSystem;
    private Date generateTime;
    
    private RateLimitStrategy recommendedStrategy;
    private Double confidenceScore;
    private String recommendationReason;
    
    private List<RateLimitStrategy> alternativeStrategies;
    private List<StrategyPerformance> historicalPerformance;
    
    private String scenarioType;
    private Map<String, Object> metrics;
    
    @Data
    public static class StrategyPerformance {
        private String strategyId;
        private String strategyName;
        private Integer drillCount;
        private Double avgScore;
        private Double bestScore;
        private Double worstScore;
        private Double avgRecoveryTimeMs;
        private Double avgErrorRate;
        private Double peakQpsHandled;
        private Date lastTestTime;
    }
}
