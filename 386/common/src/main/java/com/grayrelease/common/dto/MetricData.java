package com.grayrelease.common.dto;

import com.grayrelease.common.enums.MetricType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetricData {

    private String serviceName;

    private String version;

    private MetricType metricType;

    private Double value;

    private Double threshold;

    private Boolean isAbnormal;

    private LocalDateTime timestamp;
}