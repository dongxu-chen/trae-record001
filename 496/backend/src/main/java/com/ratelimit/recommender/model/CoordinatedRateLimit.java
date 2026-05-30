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
public class CoordinatedRateLimit {
    private String triggerServiceId;
    private String triggerReason;
    private double triggerThreshold;
    private double reductionPercentage;
    private LocalDateTime startTime;
    private LocalDateTime estimatedEndTime;
    private List<String> affectedUpstreamServices;
    private Map<String, Double> upstreamReductions;
    private CoordinationStatus status;
    private String coordinationId;

    public enum CoordinationStatus {
        TRIGGERED,
        PROPAGATING,
        ACTIVE,
        RECOVERING,
        COMPLETED
    }
}
