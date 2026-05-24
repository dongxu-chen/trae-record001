package com.abtest.dto;

import lombok.Data;

@Data
public class StatisticalResultDTO {
    private String metricName;
    private String controlVariant;
    private String testVariant;
    private Double controlValue;
    private Double testValue;
    private Double relativeChange;
    private Double absoluteChange;
    private Double pValue;
    private Double adjustedPValue;
    private Double confidenceLevel;
    private Double adjustedConfidenceLevel;
    private Double confidenceIntervalLower;
    private Double confidenceIntervalUpper;
    private Double adjustedConfidenceIntervalLower;
    private Double adjustedConfidenceIntervalUpper;
    private Boolean isStatisticallySignificant;
    private Boolean isBonferroniSignificant;
    private Integer comparisonCount;
    private Double bonferroniCorrectedAlpha;
    private String testType;
    private String significance;
    private String bonferroniSignificance;
}
