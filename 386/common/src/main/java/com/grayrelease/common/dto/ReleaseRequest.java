package com.grayrelease.common.dto;

import com.grayrelease.common.enums.ReleaseStrategy;
import com.grayrelease.common.model.MetricThreshold;
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
public class ReleaseRequest {

    private String serviceName;

    private ReleaseStrategy strategy;

    private String stableVersion;

    private String canaryVersion;

    private String canaryImage;

    private List<Integer> stepTrafficPercents;

    private Map<String, String> matchRules;

    private MetricThreshold threshold;

    private String createdBy;
}