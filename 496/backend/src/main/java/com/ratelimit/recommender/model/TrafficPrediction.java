package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TrafficPrediction {
    private List<TimeSeriesPoint> historicalData;
    private List<TimeSeriesPoint> predictedData;
    private double predictionConfidence;
    private LocalDateTime predictionTime;
    private int predictionHorizonMinutes;
}
