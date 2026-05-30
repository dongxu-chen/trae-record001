package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceTopology {
    private List<ServiceNode> nodes;
    private List<ServiceEdge> edges;
    private Map<String, List<ServiceNode>> dependencyChains;
    private List<String> criticalPath;
    private double overallHealthScore;
}
