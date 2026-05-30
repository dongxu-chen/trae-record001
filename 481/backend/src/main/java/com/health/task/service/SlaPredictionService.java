package com.health.task.service;

import com.health.task.dto.SlaPredictionResponse;
import com.health.task.entity.HealthScore;
import com.health.task.entity.SlaPrediction;
import com.health.task.model.TaskMetrics;
import com.health.task.repository.HealthScoreRepository;
import com.health.task.repository.SlaPredictionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class SlaPredictionService {

    private final SlaPredictionRepository slaPredictionRepo;
    private final HealthScoreRepository healthScoreRepo;
    private final HealthScoringService scoringService;

    private static final int DEFAULT_SLA_TARGET = 80;

    public SlaPredictionResponse predictSlaAchievement(String taskName, String taskGroup, Integer slaTarget) {
        int target = slaTarget != null ? slaTarget : DEFAULT_SLA_TARGET;

        LocalDateTime now = LocalDateTime.now();
        LocalDate today = now.toLocalDate();
        LocalDateTime monthStart = today.withDayOfMonth(1).atStartOfDay();
        LocalDateTime monthEnd = today.withDayOfMonth(today.lengthOfMonth()).atTime(23, 59, 59);

        int daysAnalyzed = (int) ChronoUnit.DAYS.between(monthStart, now) + 1;
        int daysRemaining = today.lengthOfMonth() - daysAnalyzed;

        List<HealthScore> monthlyScores = healthScoreRepo
                .findByTaskNameOrderByCalculatedAtDesc(taskName)
                .stream()
                .filter(s -> !s.getCalculatedAt().isBefore(monthStart))
                .toList();

        double currentMonthlyAvg = calculateMonthlyAverage(monthlyScores);

        LocalDateTime start24h = now.minusHours(24);
        TaskMetrics metrics = scoringService.collectMetrics(taskName, taskGroup, start24h, now);
        double currentSuccessRate = metrics.getSuccessRate();

        int healthyDays = 0, warningDays = 0, criticalDays = 0;
        for (HealthScore s : monthlyScores) {
            if (s.getOverallScore() >= 80) healthyDays++;
            else if (s.getOverallScore() >= 60) warningDays++;
            else criticalDays++;
        }

        double dailyTrend = calculateDailyTrend(monthlyScores);
        double projectedEndOfMonth = calculateProjectedEndOfMonth(currentMonthlyAvg, dailyTrend, daysRemaining);
        double bestCase = Math.min(100, currentMonthlyAvg + (100 - currentMonthlyAvg) * 0.7);
        double worstCase = Math.max(0, currentMonthlyAvg - (currentMonthlyAvg * 0.3));

        double requiredDailyScore = calculateRequiredDailyScore(currentMonthlyAvg, daysAnalyzed, daysRemaining, target);
        double requiredSuccessRate = calculateRequiredSuccessRate(currentSuccessRate, daysAnalyzed, daysRemaining);

        double achievementProbability = calculateAchievementProbability(
                currentMonthlyAvg, dailyTrend, target, daysRemaining);

        String slaStatus = determineSlaStatus(currentMonthlyAvg, projectedEndOfMonth, target, achievementProbability);
        String recommendations = generateRecommendations(
                currentMonthlyAvg, target, projectedEndOfMonth, metrics, achievementProbability);

        int predictedFailures = predictRemainingFailures(metrics, daysRemaining);

        Integer score7d = getHistoricalScore(taskName, 7);
        Integer score14d = getHistoricalScore(taskName, 14);
        Integer score30d = getHistoricalScore(taskName, 30);

        SlaPrediction prediction = SlaPrediction.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .slaTargetScore(target)
                .predictedMonthlyScore(Math.round(projectedEndOfMonth * 100.0) / 100.0)
                .currentMonthlyAvg(Math.round(currentMonthlyAvg * 100.0) / 100.0)
                .achievementProbability(Math.round(achievementProbability * 100.0) / 100.0)
                .daysRemainingInMonth(daysRemaining)
                .daysAnalyzed(daysAnalyzed)
                .currentSuccessRate(Math.round(currentSuccessRate * 100.0) / 100.0)
                .requiredSuccessRate(Math.round(requiredSuccessRate * 100.0) / 100.0)
                .predictedFailuresRemaining(predictedFailures)
                .slaStatus(slaStatus)
                .recommendations(recommendations)
                .predictionTime(now)
                .monthStart(monthStart)
                .monthEnd(monthEnd)
                .bestCaseScore(Math.round(bestCase * 100.0) / 100.0)
                .worstCaseScore(Math.round(worstCase * 100.0) / 100.0)
                .healthyDays(healthyDays)
                .warningDays(warningDays)
                .criticalDays(criticalDays)
                .build();

        slaPredictionRepo.save(prediction);

        return SlaPredictionResponse.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .slaTargetScore(target)
                .predictedMonthlyScore(prediction.getPredictedMonthlyScore())
                .currentMonthlyAvg(prediction.getCurrentMonthlyAvg())
                .achievementProbability(prediction.getAchievementProbability())
                .slaStatus(slaStatus)
                .daysRemainingInMonth(daysRemaining)
                .daysAnalyzed(daysAnalyzed)
                .currentSuccessRate(prediction.getCurrentSuccessRate())
                .requiredSuccessRate(prediction.getRequiredSuccessRate())
                .predictedFailuresRemaining(predictedFailures)
                .bestCaseScore(prediction.getBestCaseScore())
                .worstCaseScore(prediction.getWorstCaseScore())
                .healthyDays(healthyDays)
                .warningDays(warningDays)
                .criticalDays(criticalDays)
                .recommendations(recommendations)
                .predictionTime(now)
                .monthStart(monthStart)
                .monthEnd(monthEnd)
                .trendData(SlaPredictionResponse.SlaTrendData.builder()
                        .dailyScoreTrend(Math.round(dailyTrend * 100.0) / 100.0)
                        .weeklyScoreTrend(Math.round(dailyTrend * 7 * 100.0) / 100.0)
                        .score7DaysAgo(score7d)
                        .score14DaysAgo(score14d)
                        .score30DaysAgo(score30d)
                        .projectedEndOfMonthScore(Math.round(projectedEndOfMonth * 100.0) / 100.0)
                        .build())
                .build();
    }

    private double calculateMonthlyAverage(List<HealthScore> scores) {
        if (scores.isEmpty()) return 0;
        return scores.stream()
                .mapToInt(HealthScore::getOverallScore)
                .average()
                .orElse(0);
    }

    private double calculateDailyTrend(List<HealthScore> scores) {
        if (scores.size() < 2) return 0;

        List<HealthScore> sorted = scores.stream()
                .sorted((a, b) -> a.getCalculatedAt().compareTo(b.getCalculatedAt()))
                .toList();

        int n = Math.min(sorted.size(), 14);
        double[] x = new double[n];
        double[] y = new double[n];

        for (int i = 0; i < n; i++) {
            x[i] = i;
            y[i] = sorted.get(sorted.size() - n + i).getOverallScore();
        }

        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        for (int i = 0; i < n; i++) {
            sumX += x[i];
            sumY += y[i];
            sumXY += x[i] * y[i];
            sumX2 += x[i] * x[i];
        }

        double slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        return slope;
    }

    private double calculateProjectedEndOfMonth(double currentAvg, double trend, int daysRemaining) {
        double projected = currentAvg + trend * daysRemaining * 0.5;
        return Math.max(0, Math.min(100, projected));
    }

    private double calculateRequiredDailyScore(double currentAvg, int daysAnalyzed,
                                               int daysRemaining, int target) {
        if (daysRemaining <= 0) return currentAvg;
        double totalRequired = target * (daysAnalyzed + daysRemaining);
        double currentTotal = currentAvg * daysAnalyzed;
        return Math.max(0, (totalRequired - currentTotal) / daysRemaining);
    }

    private double calculateRequiredSuccessRate(double currentRate, int daysAnalyzed, int daysRemaining) {
        if (daysRemaining <= 0) return currentRate;
        double targetRate = 95.0;
        double totalRequired = targetRate * (daysAnalyzed + daysRemaining);
        double currentTotal = currentRate * daysAnalyzed;
        return Math.max(0, Math.min(100, (totalRequired - currentTotal) / daysRemaining));
    }

    private double calculateAchievementProbability(double currentAvg, double trend,
                                                    int target, int daysRemaining) {
        double gap = target - currentAvg;

        if (currentAvg >= target) {
            return Math.min(0.99, 0.85 + (currentAvg - target) / 100);
        }

        if (gap > 15) {
            return Math.max(0.01, 0.1 - gap / 200);
        }

        if (trend > 0) {
            double daysNeeded = gap / trend;
            if (daysNeeded <= daysRemaining) {
                return 0.7;
            } else {
                return 0.3 + (double) daysRemaining / daysNeeded * 0.4;
            }
        } else if (trend < 0) {
            return Math.max(0.05, 0.3 - gap / 50);
        } else {
            return Math.max(0.1, 0.5 - gap / 30);
        }
    }

    private String determineSlaStatus(double currentAvg, double projected,
                                      int target, double probability) {
        if (currentAvg >= target && probability > 0.8) {
            return "ON_TRACK";
        } else if (projected >= target * 0.95 && probability > 0.5) {
            return "AT_RISK";
        } else if (projected >= target * 0.85 && probability > 0.3) {
            return "WARNING";
        } else {
            return "LIKELY_TO_FAIL";
        }
    }

    private String generateRecommendations(double currentAvg, int target,
                                            double projected, TaskMetrics metrics,
                                            double probability) {
        List<String> recommendations = new ArrayList<>();
        double gap = target - currentAvg;

        if (probability >= 0.8) {
            recommendations.add("SLA achievement is on track. Continue monitoring for regressions.");
            if (currentAvg >= target + 5) {
                recommendations.add("Current performance exceeds target. Consider increasing SLA target.");
            }
        } else if (probability >= 0.5) {
            recommendations.add(String.format(
                    "SLA achievement is at risk. Current avg: %.1f, target: %d. Need to improve by %.1f points.",
                    currentAvg, target, gap));
            recommendations.add("Prioritize fixing high-impact issues to improve success rate.");
        } else if (probability >= 0.3) {
            recommendations.add(String.format(
                    "SLA achievement is in danger. Projected end-of-month score: %.1f.", projected));
            recommendations.add("Immediate action required to prevent SLA breach.");
        } else {
            recommendations.add(String.format(
                    "SLA breach is likely. Gap of %.1f points is too large to recover in remaining days.", gap));
            recommendations.add("Prepare SLA breach notification and mitigation plan.");
        }

        if (metrics.getSuccessRate() < 90) {
            recommendations.add(String.format(
                    "Success rate is %.1f%%. Improve success rate to at least 95%% to meet SLA.",
                    metrics.getSuccessRate()));
        }

        if (metrics.getAvgDurationMs() > 10000) {
            recommendations.add("High execution duration detected. Optimize to improve consistency.");
        }

        return String.join(" ", recommendations);
    }

    private int predictRemainingFailures(TaskMetrics metrics, int daysRemaining) {
        double dailyFailures = (metrics.getExecutionCount() * (1 - metrics.getSuccessRate() / 100)) / 1;
        return (int) Math.ceil(dailyFailures * daysRemaining);
    }

    private Integer getHistoricalScore(String taskName, int daysAgo) {
        LocalDateTime targetTime = LocalDateTime.now().minusDays(daysAgo);
        return healthScoreRepo
                .findByTaskNameOrderByCalculatedAtDesc(taskName)
                .stream()
                .filter(s -> !s.getCalculatedAt().isBefore(targetTime.minusHours(12))
                        && !s.getCalculatedAt().isAfter(targetTime.plusHours(12)))
                .findFirst()
                .map(HealthScore::getOverallScore)
                .orElse(null);
    }

    public List<SlaPrediction> getSlaPredictionHistory(String taskName, LocalDateTime since) {
        if (since != null) {
            return slaPredictionRepo.findByTaskNameAndPredictionTimeAfterOrderByPredictionTimeDesc(taskName, since);
        }
        return slaPredictionRepo.findByTaskNameOrderByPredictionTimeDesc(taskName);
    }

    public void runSlaPredictionForAllTasks() {
        List<String> taskNames = List.of("DataSyncJob", "ReportGenerateJob", "CacheCleanJob",
                "EmailNotifyJob", "LogArchiveJob", "BackupJob", "IndexRebuildJob");

        for (String taskName : taskNames) {
            try {
                predictSlaAchievement(taskName, "DEFAULT", DEFAULT_SLA_TARGET);
                log.info("SLA prediction completed for {}", taskName);
            } catch (Exception e) {
                log.warn("SLA prediction failed for {}: {}", taskName, e.getMessage());
            }
        }
    }
}
