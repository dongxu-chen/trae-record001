package com.loganalytics.model;

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
public class CustomMetric implements Serializable {
    private String metricName;
    private String expression;
    private String dimension;
    private String value;
    private double result;
    private Map<String, Double> variables;
    private long timestamp;
}
