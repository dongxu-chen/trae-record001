package com.grayrelease.common.model;

import com.grayrelease.common.enums.ReleaseStrategy;
import com.grayrelease.common.enums.ReleaseStatus;
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
public class ReleaseRecord {

    private String id;

    private String serviceName;

    private ReleaseStrategy strategy;

    private ReleaseStatus status;

    private String stableVersion;

    private String canaryVersion;

    private Integer canaryTrafficPercent;

    private List<String> stepTrafficPercents;

    private Integer currentStep;

    private Map<String, String> matchRules;

    private MetricThreshold threshold;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private String createdBy;

    private String rollbackReason;
}