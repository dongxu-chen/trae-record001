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
public class WaterLevelUpdate {
    private String type;
    private LocalDateTime timestamp;
    private Map<String, Double> waterLevels;
    private Map<String, Double> currentQps;
    private Map<String, Double> limitQps;
    private Map<String, Double> adjustedQps;
    private int activeCoordinations;
    private Map<String, Object> coordinations;
}
