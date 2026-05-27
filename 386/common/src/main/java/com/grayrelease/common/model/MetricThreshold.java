package com.grayrelease.common.model;

import com.grayrelease.common.enums.MetricType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetricThreshold {

    private MetricType metricType;

    private Double warningThreshold;

    private Double criticalThreshold;

    private Integer durationSeconds;

    private String comparison;
}