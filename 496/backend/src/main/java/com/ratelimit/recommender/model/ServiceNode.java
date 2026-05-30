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
public class ServiceNode {
    private String serviceId;
    private String serviceName;
    private String version;
    private String status;
    private List<String> dependencies;
    private List<String> dependents;
    private Map<String, ApiEndpoint> endpoints;
    private ServiceMetrics metrics;
    private LocalDateTime lastUpdate;
}
