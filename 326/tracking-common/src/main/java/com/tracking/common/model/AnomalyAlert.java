package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnomalyAlert implements Serializable {

    private static final long serialVersionUID = 1L;

    private String alertId;

    private String anomalyType;

    private String severity;

    private String metricName;

    private String dimension;

    private String dimensionValue;

    private Double currentValue;

    private Double baselineValue;

    private Double deviationPercent;

    private Double zScore;

    private Long windowStartTime;

    private Long windowEndTime;

    private Long detectionTime;

    private String description;

    private Map<String, Object> details;

    private String status;

    private String acknowledgedBy;

    private Long acknowledgedTime;

    private String comment;
}
