package com.grayrelease.common.dto;

import com.grayrelease.common.enums.ReleaseStrategy;
import com.grayrelease.common.model.MetricThreshold;
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
public class ExperimentRequest {

    private String name;

    private String description;

    private String serviceName;

    private String experimentGroup;

    private ReleaseStrategy strategy;

    private String stableVersion;

    private String experimentVersion;

    private String experimentImage;

    private int maxTrafficPercent;

    private List<Integer> stepTrafficPercents;

    private Map<String, String> trafficMatchRules;

    private List<MetricThreshold> successMetrics;

    private List<MetricThreshold> guardrailMetrics;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private String owner;

    private Map<String, String> metadata;
}