package com.loganalytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TrafficForecast implements Serializable {
    private String dimension;
    private String value;
    private double currentQps;
    private double predictedQps;
    private double predictedQpsNext;
    private double predictedQpsNext2;
    private double confidence;
    private double trendSlope;
    private double trendIntercept;
    private String trendDirection;
    private double movingAvg5;
    private double movingAvg10;
    private double deviationFromPredicted;
    private long windowStart;
    private long windowEnd;
    private long timestamp;
}
