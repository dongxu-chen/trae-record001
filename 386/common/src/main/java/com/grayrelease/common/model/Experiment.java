package com.grayrelease.common.model;

import com.grayrelease.common.enums.ExperimentStatus;
import com.grayrelease.common.enums.ReleaseStrategy;
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
public class Experiment {

    private String id;

    private String name;

    private String description;

    private String serviceName;

    private String experimentGroup;

    private ReleaseStrategy strategy;

    private ExperimentStatus status;

    private String stableVersion;

    private String experimentVersion;

    private String experimentImage;

    private int maxTrafficPercent;

    private int currentTrafficPercent;

    private List<Integer> stepTrafficPercents;

    private int currentStep;

    private Map<String, String> trafficMatchRules;

    private List<MetricThreshold> successMetrics;

    private List<MetricThreshold> guardrailMetrics;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private LocalDateTime actualEndTime;

    private String owner;

    private Map<String, String> metadata;
}