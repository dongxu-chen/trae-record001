package com.health.task.dto;

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
public class PredictionResponse {

    private String taskName;
    private String taskGroup;
    private Integer currentScore;
    private List<PredictedScorePoint> predictedScores;
    private String trendDirection;
    private Double trendSlope;
    private Double confidence;
    private String algorithmUsed;
    private LocalDateTime predictionTime;
    private Integer predictionHorizonHours;
    private String forecastSummary;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PredictedScorePoint {
        private LocalDateTime time;
        private Integer predictedScore;
        private Integer lowerBound;
        private Integer upperBound;
        private Double confidence;
    }
}
