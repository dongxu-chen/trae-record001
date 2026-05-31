package com.drill.platform.model;

import lombok.Data;
import java.util.Date;
import java.util.List;
import java.util.Map;

@Data
public class CapacityPrediction {
    private String id;
    private String targetSystem;
    private Date predictionTime;
    
    private Double currentCapacity;
    private Double safeCapacity;
    private Double maxCapacity;
    private Double capacityUtilization;
    
    private List<CapacityDataPoint> historicalData;
    private List<CapacityDataPoint> predictedData;
    
    private Double predictedPeakQps;
    private Double predictedPeakLatency;
    private Double predictedErrorRate;
    
    private String riskLevel;
    private List<String> warnings;
    private List<String> recommendations;
    
    private Map<String, Object> predictionModel;
    private Integer predictionHorizonHours;
    private Double confidence;
    
    @Data
    public static class CapacityDataPoint {
        private Date timestamp;
        private Double qps;
        private Double latencyMs;
        private Double errorRate;
        private Double cpuUsage;
        private Double memoryUsage;
        private Double threadCount;
        private String phase;
    }
    
    public enum RiskLevel {
        LOW, MEDIUM, HIGH, CRITICAL
    }
}
