package com.platform.points.vo;

import lombok.Data;

import java.util.List;

@Data
public class PointsPredictionVO {

    private Long userId;

    private Integer currentPoints;

    private List<PredictionPoint> predictionPoints;

    private Double monthlyGrowthRate;

    private String estimatedLevelUpDate;

    private String nextLevelName;

    private Integer pointsToNextLevel;

    private Integer estimatedDaysToLevelUp;

    @Data
    public static class PredictionPoint {
        private String date;
        private Integer predictedPoints;
        private Integer lowerBound;
        private Integer upperBound;
    }
}
