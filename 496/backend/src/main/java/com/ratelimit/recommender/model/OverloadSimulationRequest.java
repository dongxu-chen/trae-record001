package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OverloadSimulationRequest {
    private String serviceId;
    private double trafficMultiplier;
    private int durationSeconds;
    private List<String> affectedApis;
    private String simulationType;
}
