package com.platform.points.vo;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class PointsLeverageVO {

    private String startDate;

    private String endDate;

    private Integer totalPointsGranted;

    private Integer totalPointsConsumed;

    private Double pointsUtilizationRate;

    private Double estimatedGMV;

    private Double pointsLeverageRatio;

    private Double gmvIncrementRate;

    private List<DailyData> dailyData;

    private Map<String, Double> sourceContribution;

    private Integer activeUsers;

    private Double avgPointsPerUser;

    @Data
    public static class DailyData {
        private String date;
        private Integer pointsGranted;
        private Integer pointsConsumed;
        private Double estimatedGMV;
        private Long userCount;
    }
}
