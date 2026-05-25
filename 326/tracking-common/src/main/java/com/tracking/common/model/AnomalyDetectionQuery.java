package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnomalyDetectionQuery implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long startTime;

    private Long endTime;

    private String metricName;

    private String dimension;

    private String dimensionValue;

    private String anomalyType;

    private String severity;

    private String status;

    private Integer page;

    private Integer pageSize;
}
