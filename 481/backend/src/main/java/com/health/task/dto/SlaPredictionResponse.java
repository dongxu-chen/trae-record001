package com.health.task.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SlaPredictionResponse {

    private String taskName;
    private String taskGroup;
    private Integer slaTargetScore;
    private Double predictedMonthlyScore;
    private Double currentMonthlyAvg;
    private Double achievementProbability;
    private String slaStatus;
    private Integer daysRemainingInMonth;
    private Integer daysAnalyzed;
    private Double currentSuccessRate;
    private Double requiredSuccessRate;
    private Integer predictedFailuresRemaining;
    private Double bestCaseScore;
    private Double worstCaseScore;
    private Integer healthyDays;
    private Integer warningDays;
    private Integer criticalDays;
    private String recommendations;
    private LocalDateTime predictionTime;
    private LocalDateTime monthStart;
    private LocalDateTime monthEnd;
    private SlaTrendData trendData;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SlaTrendData {
        private Double dailyScoreTrend;
        private Double weeklyScoreTrend;
        private Integer score7DaysAgo;
        private Integer score14DaysAgo;
        private Integer score30DaysAgo;
        private Double projectedEndOfMonthScore;
    }
}
