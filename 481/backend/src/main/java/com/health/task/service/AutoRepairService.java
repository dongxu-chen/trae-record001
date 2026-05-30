package com.health.task.service;

import com.health.task.dto.AutoRepairResponse;
import com.health.task.entity.AutoRepairLog;
import com.health.task.entity.HealthScore;
import com.health.task.model.TaskMetrics;
import com.health.task.repository.AutoRepairLogRepository;
import com.health.task.repository.HealthScoreRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class AutoRepairService {

    private final AutoRepairLogRepository repairLogRepo;
    private final HealthScoreRepository healthScoreRepo;
    private final HealthScoringService scoringService;

    private static final int DEFAULT_MAX_RETRIES = 3;
    private static final long DEFAULT_RETRY_DELAY_MS = 1000;
    private static final long DEFAULT_TIMEOUT_MS = 30000;

    private static final double SUCCESS_RATE_THRESHOLD = 85.0;
    private static final double TIMEOUT_RATE_THRESHOLD = 10.0;
    private static final long DURATION_THRESHOLD_MS = 15000;

    private final Map<String, RepairConfig> currentConfigs = new HashMap<>();

    public AutoRepairResponse analyzeAndRepair(String taskName, String taskGroup) {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime since = now.minusHours(24);

        TaskMetrics metrics = scoringService.collectMetrics(taskName, taskGroup, since, now);
        HealthScore latestScore = healthScoreRepo.findTopByTaskNameOrderByCalculatedAtDesc(taskName)
                .orElse(null);

        RepairConfig config = currentConfigs.computeIfAbsent(taskName,
                k -> new RepairConfig(DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY_MS, DEFAULT_TIMEOUT_MS));

        List<AutoRepairLog> repairs = new ArrayList<>();

        if (metrics.getSuccessRate() < SUCCESS_RATE_THRESHOLD) {
            AutoRepairLog repair = handleLowSuccessRate(taskName, taskGroup, metrics, config);
            if (repair != null) {
                repairs.add(repair);
            }
        }

        if (metrics.getAvgDurationMs() > DURATION_THRESHOLD_MS) {
            AutoRepairLog repair = handleHighDuration(taskName, taskGroup, metrics, config);
            if (repair != null) {
                repairs.add(repair);
            }
        }

        if (metrics.getDurationVariance() > 5000000) {
            AutoRepairLog repair = handleHighVariance(taskName, taskGroup, metrics, config);
            if (repair != null) {
                repairs.add(repair);
            }
        }

        repairs.forEach(repairLogRepo::save);

        long totalRepairs = repairLogRepo.countByTaskNameAndStatus(taskName, "SUCCESS");
        long failedRepairs = repairLogRepo.countByTaskNameAndStatus(taskName, "FAILED");

        String status = calculateAutoRepairStatus(metrics, latestScore);

        return AutoRepairResponse.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .autoRepairCount((int) (totalRepairs + failedRepairs))
                .successfulRepairs((int) totalRepairs)
                .failedRepairs((int) failedRepairs)
                .recentRepairs(buildRecentRepairs(taskName))
                .currentConfig(AutoRepairResponse.CurrentRepairConfig.builder()
                        .maxRetries(config.maxRetries)
                        .retryDelayMs(config.retryDelayMs)
                        .timeoutMs(config.timeoutMs)
                        .currentSuccessRate(Math.round(metrics.getSuccessRate() * 100.0) / 100.0)
                        .currentScore(latestScore != null ? String.valueOf(latestScore.getOverallScore()) : "N/A")
                        .autoRepairEnabled(true)
                        .build())
                .autoRepairStatus(status)
                .recommendations(generateRecommendations(metrics, config, repairs))
                .build();
    }

    private AutoRepairLog handleLowSuccessRate(String taskName, String taskGroup,
                                                TaskMetrics metrics, RepairConfig config) {
        int oldRetries = config.maxRetries;
        int newRetries = Math.min(oldRetries + 1, 5);

        long oldDelay = config.retryDelayMs;
        long newDelay = (long) (oldDelay * 1.5);

        config.maxRetries = newRetries;
        config.retryDelayMs = newDelay;

        return AutoRepairLog.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .failureType("LOW_SUCCESS_RATE")
                .repairAction("INCREASE_RETRY_PARAMETERS")
                .oldValue(String.format("retries=%d, delay=%dms", oldRetries, oldDelay))
                .newValue(String.format("retries=%d, delay=%dms", newRetries, newDelay))
                .repairTime(LocalDateTime.now())
                .status("SUCCESS")
                .repairDetails(String.format(
                        "Success rate is %.1f%% (threshold: %.1f%%). Increased max retries from %d to %d and retry delay from %dms to %dms with exponential backoff.",
                        metrics.getSuccessRate(), SUCCESS_RATE_THRESHOLD, oldRetries, newRetries, oldDelay, newDelay))
                .maxRetriesBefore(oldRetries)
                .maxRetriesAfter(newRetries)
                .retryDelayMsBefore(oldDelay)
                .retryDelayMsAfter(newDelay)
                .riskLevel("MEDIUM")
                .build();
    }

    private AutoRepairLog handleHighDuration(String taskName, String taskGroup,
                                              TaskMetrics metrics, RepairConfig config) {
        long oldTimeout = config.timeoutMs;
        long newTimeout = (long) (oldTimeout * 1.3);

        config.timeoutMs = newTimeout;

        return AutoRepairLog.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .failureType("HIGH_DURATION")
                .repairAction("INCREASE_TIMEOUT")
                .oldValue(String.format("%dms", oldTimeout))
                .newValue(String.format("%dms", newTimeout))
                .repairTime(LocalDateTime.now())
                .status("SUCCESS")
                .repairDetails(String.format(
                        "Average execution duration is %dms (threshold: %dms). Increased timeout from %dms to %dms to prevent premature timeout failures.",
                        (long) metrics.getAvgDurationMs(), DURATION_THRESHOLD_MS, oldTimeout, newTimeout))
                .timeoutMsBefore(oldTimeout)
                .timeoutMsAfter(newTimeout)
                .riskLevel("LOW")
                .build();
    }

    private AutoRepairLog handleHighVariance(String taskName, String taskGroup,
                                              TaskMetrics metrics, RepairConfig config) {
        int oldRetries = config.maxRetries;
        int newRetries = Math.min(oldRetries + 1, 5);

        long oldDelay = config.retryDelayMs;
        long newDelay = (long) (oldDelay * 2);

        config.maxRetries = newRetries;
        config.retryDelayMs = newDelay;

        return AutoRepairLog.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .failureType("HIGH_VARIANCE")
                .repairAction("INCREASE_RETRY_AND_DELAY")
                .oldValue(String.format("retries=%d, delay=%dms", oldRetries, oldDelay))
                .newValue(String.format("retries=%d, delay=%dms", newRetries, newDelay))
                .repairTime(LocalDateTime.now())
                .status("SUCCESS")
                .repairDetails(String.format(
                        "High execution variance detected (variance: %.0f). Increased retry attempts and delay to handle inconsistent performance.",
                        metrics.getDurationVariance()))
                .maxRetriesBefore(oldRetries)
                .maxRetriesAfter(newRetries)
                .retryDelayMsBefore(oldDelay)
                .retryDelayMsAfter(newDelay)
                .riskLevel("MEDIUM")
                .build();
    }

    public AutoRepairLog applyManualRepair(String taskName, String taskGroup,
                                            String repairAction, String oldValue, String newValue,
                                            String riskLevel) {
        AutoRepairLog repair = AutoRepairLog.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .failureType("MANUAL")
                .repairAction(repairAction)
                .oldValue(oldValue)
                .newValue(newValue)
                .repairTime(LocalDateTime.now())
                .status("PENDING")
                .repairDetails("Manual repair requested by operator")
                .riskLevel(riskLevel != null ? riskLevel : "MEDIUM")
                .build();

        return repairLogRepo.save(repair);
    }

    public String updateRepairStatus(Long repairId, String status, Double successRateAfter, Integer followUpScore) {
        AutoRepairLog repair = repairLogRepo.findById(repairId).orElse(null);
        if (repair == null) {
            return "Repair not found";
        }

        repair.setStatus(status);
        if (successRateAfter != null) {
            repair.setSuccessRateAfterRepair(successRateAfter);
        }
        if (followUpScore != null) {
            repair.setFollowUpScore(followUpScore);
        }

        repairLogRepo.save(repair);
        return "Repair status updated successfully";
    }

    public List<AutoRepairLog> getRepairHistory(String taskName, LocalDateTime since) {
        if (since != null) {
            return repairLogRepo.findByTaskNameAndRepairTimeAfterOrderByRepairTimeDesc(taskName, since);
        }
        return repairLogRepo.findByTaskNameOrderByRepairTimeDesc(taskName);
    }

    public void runAutoRepairForAllTasks() {
        List<String> taskNames = List.of("DataSyncJob", "ReportGenerateJob", "CacheCleanJob",
                "EmailNotifyJob", "LogArchiveJob", "BackupJob", "IndexRebuildJob");

        for (String taskName : taskNames) {
            try {
                analyzeAndRepair(taskName, "DEFAULT");
                log.info("Auto-repair analysis completed for {}", taskName);
            } catch (Exception e) {
                log.warn("Auto-repair failed for {}: {}", taskName, e.getMessage());
            }
        }
    }

    private List<AutoRepairResponse.AutoRepairDetail> buildRecentRepairs(String taskName) {
        return repairLogRepo.findByTaskNameOrderByRepairTimeDesc(taskName)
                .stream()
                .limit(10)
                .map(log -> AutoRepairResponse.AutoRepairDetail.builder()
                        .id(log.getId())
                        .failureType(log.getFailureType())
                        .repairAction(log.getRepairAction())
                        .oldValue(log.getOldValue())
                        .newValue(log.getNewValue())
                        .repairTime(log.getRepairTime())
                        .status(log.getStatus())
                        .riskLevel(log.getRiskLevel())
                        .successRateAfter(log.getSuccessRateAfterRepair())
                        .build())
                .toList();
    }

    private String calculateAutoRepairStatus(TaskMetrics metrics, HealthScore latestScore) {
        if (latestScore == null) return "UNKNOWN";

        int score = latestScore.getOverallScore();
        double successRate = metrics.getSuccessRate();

        if (score >= 80 && successRate >= 95) {
            return "HEALTHY";
        } else if (score >= 60 && successRate >= 85) {
            return "STABLE";
        } else if (score >= 40 && successRate >= 70) {
            return "NEEDS_ATTENTION";
        } else {
            return "CRITICAL";
        }
    }

    private String generateRecommendations(TaskMetrics metrics, RepairConfig config, List<AutoRepairLog> repairs) {
        List<String> recommendations = new ArrayList<>();

        if (metrics.getSuccessRate() < 80) {
            recommendations.add("Consider adding circuit breaker pattern to prevent cascading failures");
            recommendations.add("Review recent error logs to identify root cause of failures");
        }

        if (metrics.getAvgDurationMs() > 10000) {
            recommendations.add("Profile task execution to identify performance bottlenecks");
            recommendations.add("Consider implementing batch processing for large datasets");
        }

        if (config.maxRetries >= 5) {
            recommendations.add("Max retries reached upper limit. Consider addressing root cause instead of increasing retries");
        }

        if (repairs.size() > 5) {
            recommendations.add(String.format("Multiple auto-repairs applied (%d). Consider manual review of task configuration", repairs.size()));
        }

        if (recommendations.isEmpty()) {
            recommendations.add("Task parameters are well-tuned. Continue monitoring for regressions.");
        }

        return String.join("; ", recommendations);
    }

    public RepairConfig getCurrentConfig(String taskName) {
        return currentConfigs.computeIfAbsent(taskName,
                k -> new RepairConfig(DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY_MS, DEFAULT_TIMEOUT_MS));
    }

    public static class RepairConfig {
        int maxRetries;
        long retryDelayMs;
        long timeoutMs;

        RepairConfig(int maxRetries, long retryDelayMs, long timeoutMs) {
            this.maxRetries = maxRetries;
            this.retryDelayMs = retryDelayMs;
            this.timeoutMs = timeoutMs;
        }
    }
}
