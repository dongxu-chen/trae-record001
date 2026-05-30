package com.health.task.service;

import com.health.task.dto.HealthScoreResponse;
import com.health.task.entity.HealthScore;
import com.health.task.entity.OptimizationScript;
import com.health.task.entity.TaskDependency;
import com.health.task.entity.TaskExecutionRecord;
import com.health.task.entity.TaskWeightConfig;
import com.health.task.model.DimensionScore;
import com.health.task.model.HealthScoreResult;
import com.health.task.model.TaskMetrics;
import com.health.task.repository.HealthScoreRepository;
import com.health.task.repository.OptimizationScriptRepository;
import com.health.task.repository.TaskDependencyRepository;
import com.health.task.repository.TaskExecutionRecordRepository;
import com.health.task.repository.TaskWeightConfigRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Slf4j
public class HealthScoringService {

    private final TaskExecutionRecordRepository executionRepo;
    private final HealthScoreRepository healthScoreRepo;
    private final TaskWeightConfigRepository weightConfigRepo;
    private final TaskDependencyRepository dependencyRepo;
    private final OptimizationScriptRepository scriptRepo;

    private static final double DEFAULT_DURATION_WEIGHT = 0.25;
    private static final double DEFAULT_SUCCESS_RATE_WEIGHT = 0.35;
    private static final double DEFAULT_FREQUENCY_WEIGHT = 0.15;
    private static final double DEFAULT_RESOURCE_WEIGHT = 0.25;

    private static final long EXPECTED_DURATION_MS = 5000;
    private static final long DURATION_TOLERANCE_MS = 10000;
    private static final double EXPECTED_CPU_PERCENT = 50.0;
    private static final double EXPECTED_MEMORY_MB = 256.0;
    private static final int EXPECTED_DAILY_EXECUTIONS = 24;

    public HealthScoreResult calculateScore(String taskName, String taskGroup, LocalDateTime since) {
        LocalDateTime end = LocalDateTime.now();
        LocalDateTime start = since != null ? since : end.minusHours(24);

        TaskWeightConfig weightConfig = weightConfigRepo.findByTaskName(taskName).orElse(null);
        double durationWeight = weightConfig != null ? weightConfig.getDurationWeight() : DEFAULT_DURATION_WEIGHT;
        double successRateWeight = weightConfig != null ? weightConfig.getSuccessRateWeight() : DEFAULT_SUCCESS_RATE_WEIGHT;
        double frequencyWeight = weightConfig != null ? weightConfig.getFrequencyWeight() : DEFAULT_FREQUENCY_WEIGHT;
        double resourceWeight = weightConfig != null ? weightConfig.getResourceWeight() : DEFAULT_RESOURCE_WEIGHT;

        TaskMetrics metrics = collectMetrics(taskName, taskGroup, start, end);
        List<DimensionScore> dimensions = new ArrayList<>();

        DimensionScore durationScore = scoreDuration(metrics, durationWeight);
        dimensions.add(durationScore);

        DimensionScore successRateScore = scoreSuccessRate(metrics, successRateWeight);
        dimensions.add(successRateScore);

        DimensionScore frequencyScore = scoreFrequency(metrics, frequencyWeight);
        dimensions.add(frequencyScore);

        DimensionScore resourceScore = scoreResource(metrics, resourceWeight);
        dimensions.add(resourceScore);

        int overall = (int) dimensions.stream()
                .mapToDouble(d -> d.getScore() * d.getWeight())
                .sum();

        overall = Math.max(0, Math.min(100, overall));

        String diagnosis = diagnose(metrics, overall);
        String suggestion = suggest(metrics, overall);

        return HealthScoreResult.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .overallScore(overall)
                .dimensionScores(dimensions)
                .diagnosis(diagnosis)
                .suggestion(suggestion)
                .build();
    }

    public void calculateAndSaveAllScores() {
        List<String> taskNames = executionRepo.findAllTaskNames();
        LocalDateTime since = LocalDateTime.now().minusHours(24);

        for (String taskName : List.of("DataSyncJob", "ReportGenerateJob", "CacheCleanJob",
                "EmailNotifyJob", "LogArchiveJob", "BackupJob", "IndexRebuildJob")) {
            try {
                HealthScoreResult result = calculateScore(taskName, "DEFAULT", since);
                saveScore(result);
                log.info("Calculated health score for task {}: {}", taskName, result.getOverallScore());
            } catch (Exception e) {
                log.warn("Failed to calculate score for task {}: {}", taskName, e.getMessage());
            }
        }
    }

    public void saveScore(HealthScoreResult result) {
        HealthScore entity = HealthScore.builder()
                .taskName(result.getTaskName())
                .taskGroup(result.getTaskGroup())
                .overallScore(result.getOverallScore())
                .durationScore(findDimensionScore(result, "duration"))
                .successRateScore(findDimensionScore(result, "success_rate"))
                .frequencyScore(findDimensionScore(result, "frequency"))
                .resourceScore(findDimensionScore(result, "resource"))
                .calculatedAt(LocalDateTime.now())
                .diagnosis(result.getDiagnosis())
                .suggestion(result.getSuggestion())
                .build();
        healthScoreRepo.save(entity);
    }

    public List<HealthScore> getScoreTrend(String taskName, int hours) {
        LocalDateTime start = LocalDateTime.now().minusHours(hours);
        return healthScoreRepo.findByTaskNameAndCalculatedAtBetweenOrderByCalculatedAtAsc(
                taskName, start, LocalDateTime.now());
    }

    public List<HealthScore> getLatestScores() {
        return healthScoreRepo.findLatestScoresForAllTasks();
    }

    public List<HealthScore> getUnhealthyTasks(int threshold) {
        return healthScoreRepo.findUnhealthyTasks(threshold);
    }

    public TaskMetrics collectMetrics(String taskName, String taskGroup, LocalDateTime start, LocalDateTime end) {
        long totalExecutions = executionRepo.countByTaskNameAndTimeRange(taskName, start, end);
        long successExecutions = executionRepo.countSuccessByTaskNameAndTimeRange(taskName, start, end);

        double successRate = totalExecutions > 0
                ? (double) successExecutions / totalExecutions * 100.0
                : 0.0;

        Double avgDuration = executionRepo.avgDurationByTaskNameAndTimeRange(taskName, start, end);
        Long maxDuration = executionRepo.maxDurationByTaskNameAndTimeRange(taskName, start, end);
        Double avgCpu = executionRepo.avgCpuByTaskNameAndTimeRange(taskName, start, end);
        Double avgMemory = executionRepo.avgMemoryByTaskNameAndTimeRange(taskName, start, end);

        List<TaskExecutionRecord> records = executionRepo.findByTaskNameAndCreatedAtBetweenOrderByCreatedAtDesc(
                taskName, start, end);
        double variance = calculateDurationVariance(records, avgDuration != null ? avgDuration : 0.0);

        return TaskMetrics.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .avgDurationMs(avgDuration != null ? avgDuration : 0.0)
                .maxDurationMs(maxDuration != null ? maxDuration : 0L)
                .successRate(successRate)
                .executionCount((int) totalExecutions)
                .avgCpuUsage(avgCpu != null ? avgCpu : 0.0)
                .avgMemoryUsage(avgMemory != null ? avgMemory : 0.0)
                .durationVariance(variance)
                .build();
    }

    private DimensionScore scoreDuration(TaskMetrics metrics, double weight) {
        double avgDuration = metrics.getAvgDurationMs();
        double ratio = avgDuration / EXPECTED_DURATION_MS;
        int score;

        if (ratio <= 1.0) {
            score = 100;
        } else if (ratio <= 2.0) {
            score = (int) (100 - (ratio - 1.0) * 50);
        } else if (ratio <= 5.0) {
            score = (int) (50 - (ratio - 2.0) * 10);
        } else {
            score = 10;
        }

        double variancePenalty = Math.min(20, metrics.getDurationVariance() / 1000000.0 * 5);
        score = Math.max(0, (int) (score - variancePenalty));

        String detail = String.format("avg=%dms, max=%dms, variance=%.1f",
                (long) avgDuration, metrics.getMaxDurationMs(), metrics.getDurationVariance());

        return DimensionScore.builder()
                .dimensionName("duration")
                .score(score)
                .weight(weight)
                .weightedScore(score * weight)
                .detail(detail)
                .build();
    }

    private DimensionScore scoreSuccessRate(TaskMetrics metrics, double weight) {
        double rate = metrics.getSuccessRate();
        int score;

        if (rate >= 99.0) {
            score = 100;
        } else if (rate >= 95.0) {
            score = (int) (100 - (99.0 - rate) * 6);
        } else if (rate >= 80.0) {
            score = (int) (76 - (95.0 - rate) * 3);
        } else if (rate >= 50.0) {
            score = (int) (31 - (80.0 - rate) * 0.6);
        } else {
            score = 5;
        }

        String detail = String.format("rate=%.1f%%, total=%d", rate, metrics.getExecutionCount());

        return DimensionScore.builder()
                .dimensionName("success_rate")
                .score(score)
                .weight(weight)
                .weightedScore(score * weight)
                .detail(detail)
                .build();
    }

    private DimensionScore scoreFrequency(TaskMetrics metrics, double weight) {
        int count = metrics.getExecutionCount();
        int score;

        double ratio = (double) count / EXPECTED_DAILY_EXECUTIONS;
        if (ratio >= 0.8 && ratio <= 1.5) {
            score = 100;
        } else if (ratio >= 0.5 && ratio < 0.8) {
            score = (int) (60 + (ratio - 0.5) / 0.3 * 40);
        } else if (ratio > 1.5 && ratio <= 3.0) {
            score = (int) (100 - (ratio - 1.5) / 1.5 * 40);
        } else if (ratio < 0.5 && ratio > 0) {
            score = (int) (ratio / 0.5 * 60);
        } else {
            score = count == 0 ? 0 : 20;
        }

        String detail = String.format("count=%d/24h, expected=%d/24h", count, EXPECTED_DAILY_EXECUTIONS);

        return DimensionScore.builder()
                .dimensionName("frequency")
                .score(score)
                .weight(weight)
                .weightedScore(score * weight)
                .detail(detail)
                .build();
    }

    private DimensionScore scoreResource(TaskMetrics metrics, double weight) {
        double cpu = metrics.getAvgCpuUsage();
        double memory = metrics.getAvgMemoryUsage();
        int cpuScore, memoryScore;

        if (cpu <= EXPECTED_CPU_PERCENT * 0.5) {
            cpuScore = 100;
        } else if (cpu <= EXPECTED_CPU_PERCENT) {
            cpuScore = (int) (100 - (cpu / EXPECTED_CPU_PERCENT - 0.5) * 40);
        } else if (cpu <= EXPECTED_CPU_PERCENT * 2) {
            cpuScore = (int) (60 - (cpu / EXPECTED_CPU_PERCENT - 1.0) * 30);
        } else {
            cpuScore = 10;
        }

        if (memory <= EXPECTED_MEMORY_MB * 0.5) {
            memoryScore = 100;
        } else if (memory <= EXPECTED_MEMORY_MB) {
            memoryScore = (int) (100 - (memory / EXPECTED_MEMORY_MB - 0.5) * 40);
        } else if (memory <= EXPECTED_MEMORY_MB * 2) {
            memoryScore = (int) (60 - (memory / EXPECTED_MEMORY_MB - 1.0) * 30);
        } else {
            memoryScore = 10;
        }

        int score = (cpuScore + memoryScore) / 2;

        String detail = String.format("cpu=%.1f%%, memory=%.1fMB", cpu, memory);

        return DimensionScore.builder()
                .dimensionName("resource")
                .score(score)
                .weight(weight)
                .weightedScore(score * weight)
                .detail(detail)
                .build();
    }

    private String diagnose(TaskMetrics metrics, int overallScore) {
        List<String> issues = new ArrayList<>();

        if (metrics.getSuccessRate() < 80) {
            issues.add(String.format("Success rate critically low (%.1f%%)", metrics.getSuccessRate()));
        } else if (metrics.getSuccessRate() < 95) {
            issues.add(String.format("Success rate below optimal (%.1f%%)", metrics.getSuccessRate()));
        }

        if (metrics.getAvgDurationMs() > EXPECTED_DURATION_MS * 3) {
            issues.add(String.format("Execution duration extremely high (avg %dms)", (long) metrics.getAvgDurationMs()));
        } else if (metrics.getAvgDurationMs() > EXPECTED_DURATION_MS * 1.5) {
            issues.add(String.format("Execution duration above normal (avg %dms)", (long) metrics.getAvgDurationMs()));
        }

        if (metrics.getAvgCpuUsage() > EXPECTED_CPU_PERCENT * 1.5) {
            issues.add(String.format("High CPU usage (%.1f%%)", metrics.getAvgCpuUsage()));
        }

        if (metrics.getAvgMemoryUsage() > EXPECTED_MEMORY_MB * 1.5) {
            issues.add(String.format("High memory usage (%.1fMB)", metrics.getAvgMemoryUsage()));
        }

        if (metrics.getExecutionCount() == 0) {
            issues.add("No executions in the analysis period - task may be stuck or disabled");
        } else if (metrics.getExecutionCount() < EXPECTED_DAILY_EXECUTIONS * 0.5) {
            issues.add(String.format("Low execution frequency (%d times in 24h)", metrics.getExecutionCount()));
        }

        if (metrics.getDurationVariance() > 10000000) {
            issues.add("High execution duration variance - inconsistent performance");
        }

        if (issues.isEmpty()) {
            return "Task is healthy with no significant issues detected";
        }

        return String.join("; ", issues);
    }

    private String suggest(TaskMetrics metrics, int overallScore) {
        List<String> suggestions = new ArrayList<>();

        if (metrics.getSuccessRate() < 80) {
            suggestions.add("Investigate and fix error causes; add retry mechanism and circuit breaker");
        } else if (metrics.getSuccessRate() < 95) {
            suggestions.add("Review error logs for recurring patterns; improve error handling");
        }

        if (metrics.getAvgDurationMs() > EXPECTED_DURATION_MS * 3) {
            suggestions.add("Optimize task logic: add batching, use async processing, reduce DB queries");
        } else if (metrics.getAvgDurationMs() > EXPECTED_DURATION_MS * 1.5) {
            suggestions.add("Profile slow operations; consider caching or query optimization");
        }

        if (metrics.getAvgCpuUsage() > EXPECTED_CPU_PERCENT * 1.5) {
            suggestions.add("Reduce CPU load: throttle processing rate, use connection pooling");
        }

        if (metrics.getAvgMemoryUsage() > EXPECTED_MEMORY_MB * 1.5) {
            suggestions.add("Reduce memory usage: process data in chunks, check for memory leaks");
        }

        if (metrics.getExecutionCount() == 0) {
            suggestions.add("Check task scheduling configuration and ensure the task is enabled");
        } else if (metrics.getExecutionCount() < EXPECTED_DAILY_EXECUTIONS * 0.5) {
            suggestions.add("Review cron expression and ensure task triggers as expected");
        }

        if (metrics.getDurationVariance() > 10000000) {
            suggestions.add("Investigate variance causes: check for resource contention or data size fluctuations");
        }

        if (overallScore >= 90) {
            suggestions.add("Task performing well - continue monitoring for regressions");
        }

        if (suggestions.isEmpty()) {
            return "No specific optimizations needed at this time";
        }

        return String.join("; ", suggestions);
    }

    private double calculateDurationVariance(List<TaskExecutionRecord> records, double avg) {
        if (records.isEmpty()) return 0.0;
        double sum = 0;
        for (TaskExecutionRecord r : records) {
            double diff = r.getDurationMs() - avg;
            sum += diff * diff;
        }
        return sum / records.size();
    }

    private int findDimensionScore(HealthScoreResult result, String dimensionName) {
        return result.getDimensionScores().stream()
                .filter(d -> d.getDimensionName().equals(dimensionName))
                .findFirst()
                .map(DimensionScore::getScore)
                .orElse(0);
    }

    public TaskWeightConfig saveWeightConfig(String taskName, String taskGroup, String importanceLevel,
                                     Double durationWeight, Double successRateWeight,
                                     Double frequencyWeight, Double resourceWeight,
                                     String description) {
        if (Math.abs(durationWeight + successRateWeight + frequencyWeight + resourceWeight - 1.0) > 0.01) {
            throw new IllegalArgumentException("Weights must sum to 1.0");
        }
        TaskWeightConfig existing = weightConfigRepo.findByTaskName(taskName).orElse(null);
        TaskWeightConfig config = existing != null ? existing : new TaskWeightConfig();
        config.setTaskName(taskName);
        config.setTaskGroup(taskGroup);
        config.setImportanceLevel(importanceLevel);
        config.setDurationWeight(durationWeight);
        config.setSuccessRateWeight(successRateWeight);
        config.setFrequencyWeight(frequencyWeight);
        config.setResourceWeight(resourceWeight);
        config.setDescription(description);
        return weightConfigRepo.save(config);
    }

    public TaskWeightConfig getWeightConfig(String taskName) {
        return weightConfigRepo.findByTaskName(taskName).orElse(null);
    }

    public TaskDependency saveDependency(String taskName, String upstreamTaskName,
                                    String dependencyType, Integer maxWaitSeconds,
                                    String description) {
        TaskDependency dep = new TaskDependency();
        dep.setTaskName(taskName);
        dep.setUpstreamTaskName(upstreamTaskName);
        dep.setDependencyType(dependencyType);
        dep.setMaxWaitSeconds(maxWaitSeconds);
        dep.setDescription(description);
        return dependencyRepo.save(dep);
    }

    public List<TaskDependency> getDependencies(String taskName) {
        return dependencyRepo.findByTaskName(taskName);
    }

    public List<HealthScoreResponse.UpstreamIssue> checkUpstreamIssues(String taskName) {
        List<TaskDependency> deps = dependencyRepo.findByTaskName(taskName);
        List<HealthScoreResponse.UpstreamIssue> issues = new ArrayList<>();
        for (TaskDependency dep : deps) {
            Optional<HealthScore> upstreamScore = healthScoreRepo.findTopByTaskNameOrderByCalculatedAtDesc(dep.getUpstreamTaskName());
            if (upstreamScore.isPresent()) {
                HealthScore score = upstreamScore.get();
                int upScore = score.getOverallScore();
                String upLevel = getScoreLevel(upScore);
                if (upScore < 60) {
                    String issueDesc = String.format("Upstream task %s is unhealthy (score: %d, level: %s). This may affect %s",
                            dep.getUpstreamTaskName(), upScore, upLevel, taskName);
                    issues.add(HealthScoreResponse.UpstreamIssue.builder()
                            .upstreamTaskName(dep.getUpstreamTaskName())
                            .dependencyType(dep.getDependencyType())
                            .issue(issueDesc)
                            .upstreamScore(upScore)
                            .upstreamScoreLevel(upLevel)
                            .build());
                }
                if (score.getSuccessRateScore() < 80) {
                    String issueDesc = String.format("Upstream task %s has low success rate. This may cause cascading failures in %s",
                            dep.getUpstreamTaskName(), taskName);
                    issues.add(HealthScoreResponse.UpstreamIssue.builder()
                            .upstreamTaskName(dep.getUpstreamTaskName())
                            .dependencyType(dep.getDependencyType())
                            .issue(issueDesc)
                            .upstreamScore(upScore)
                            .upstreamScoreLevel(upLevel)
                            .build());
                }
            }
        }
        return issues;
    }

    public List<HealthScoreResponse.ActionableItem> generateActionableItems(TaskMetrics metrics, int overallScore) {
        List<HealthScoreResponse.ActionableItem> items = new ArrayList<>();
        int priority = 1;

        if (metrics.getSuccessRate() < 80) {
            OptimizationScript script = scriptRepo.findByIssueCategory("LOW_SUCCESS_RATE").stream().findFirst().orElse(null);
            items.add(HealthScoreResponse.ActionableItem.builder()
                    .title("添加重试机制和熔断保护")
                    .description("为任务添加指数退避重试和断路器模式，防止级联失败")
                    .scriptType(script != null ? script.getScriptType() : "JAVA")
                    .scriptName(script != null ? script.getScriptName() : "RetryAndCircuitBreaker.java")
                    .scriptContent(script != null ? script.getScriptContent() : getDefaultRetryScript())
                    .executionCommand(script != null ? script.getExecutionCommand() : "将代码集成到任务类中并配置重试参数")
                    .riskLevel("MEDIUM")
                    .priority(priority++)
                    .build());
        }

        if (metrics.getAvgDurationMs() > EXPECTED_DURATION_MS * 3) {
            OptimizationScript script = scriptRepo.findByIssueCategory("HIGH_DURATION").stream().findFirst().orElse(null);
            items.add(HealthScoreResponse.ActionableItem.builder()
                    .title("SQL查询优化和批处理")
                    .description("优化慢查询，添加批处理和分页处理，使用异步处理")
                    .scriptType(script != null ? script.getScriptType() : "SQL")
                    .scriptName(script != null ? script.getScriptName() : "optimize_queries.sql")
                    .scriptContent(script != null ? script.getScriptContent() : getDefaultSqlOptimizationScript())
                    .executionCommand(script != null ? script.getExecutionCommand() : "在数据库执行SQL优化脚本")
                    .riskLevel("MEDIUM")
                    .priority(priority++)
                    .build());
        }

        if (metrics.getAvgCpuUsage() > EXPECTED_CPU_PERCENT * 1.5) {
            OptimizationScript script = scriptRepo.findByIssueCategory("HIGH_CPU").stream().findFirst().orElse(null);
            items.add(HealthScoreResponse.ActionableItem.builder()
                    .title("CPU限流和连接池优化")
                    .description("限制任务处理速率，优化连接池配置")
                    .scriptType(script != null ? script.getScriptType() : "SHELL")
                    .scriptName(script != null ? script.getScriptName() : "throttle_and_pool.sh")
                    .scriptContent(script != null ? script.getScriptContent() : getDefaultCpuOptimizationScript())
                    .executionCommand(script != null ? script.getExecutionCommand() : "chmod +x throttle_and_pool.sh && ./throttle_and_pool.sh")
                    .riskLevel("MEDIUM")
                    .priority(priority++)
                    .build());
        }

        if (metrics.getAvgMemoryUsage() > EXPECTED_MEMORY_MB * 1.5) {
            OptimizationScript script = scriptRepo.findByIssueCategory("HIGH_MEMORY").stream().findFirst().orElse(null);
            items.add(HealthScoreResponse.ActionableItem.builder()
                    .title("内存优化和流式处理")
                    .description("使用流式处理减少内存占用，添加内存泄漏检测")
                    .scriptType(script != null ? script.getScriptType() : "JAVA")
                    .scriptName(script != null ? script.getScriptName() : "StreamProcessor.java")
                    .scriptContent(script != null ? script.getScriptContent() : getDefaultMemoryOptimizationScript())
                    .executionCommand(script != null ? script.getExecutionCommand() : "重构任务实现类，添加流式处理")
                    .riskLevel("MEDIUM")
                    .priority(priority++)
                    .build());
        }

        if (metrics.getExecutionCount() == 0) {
            OptimizationScript script = scriptRepo.findByIssueCategory("NO_EXECUTION").stream().findFirst().orElse(null);
            items.add(HealthScoreResponse.ActionableItem.builder()
                    .title("检查调度配置")
                    .description("验证Quartz调度配置，确保任务已启用")
                    .scriptType(script != null ? script.getScriptType() : "SQL")
                    .scriptName(script != null ? script.getScriptName() : "check_scheduler.sql")
                    .scriptContent(script != null ? script.getScriptContent() : getDefaultSchedulerCheckScript())
                    .executionCommand(script != null ? script.getExecutionCommand() : "检查Quartz配置并重新启动任务调度")
                    .riskLevel("HIGH")
                    .priority(priority++)
                    .build());
        }

        if (overallScore >= 90) {
            items.add(HealthScoreResponse.ActionableItem.builder()
                    .title("继续监控")
                    .description("任务运行良好，设置告警阈值监控")
                    .scriptType("CONFIG")
                    .scriptName("monitoring_alerts.yml")
                    .scriptContent(getDefaultMonitoringConfig())
                    .executionCommand("将配置集成到监控系统中")
                    .riskLevel("LOW")
                    .priority(priority++)
                    .build());
        }

        return items;
    }

    private String getScoreLevel(int score) {
        if (score >= 90) return "HEALTHY";
        if (score >= 80) return "GOOD";
        if (score >= 60) return "WARNING";
        if (score >= 40) return "POOR";
        return "CRITICAL";
    }

    private String getDefaultRetryScript() {
        return "@Retry(maxAttempts = 3, backoff = @Backoff(delay = 1000, multiplier = 2))\n" +
                "@CircuitBreaker(requestVolumeThreshold = 20, failureRatio = 0.5))\n" +
                "public void executeWithRetry() {\n" +
                "    // 重试逻辑\n" +
                "}";
    }

    private String getDefaultSqlOptimizationScript() {
        return "-- 创建索引\n" +
                "CREATE INDEX IF NOT EXISTS idx_task_execution_time ON task_execution_record(task_name, created_at);\n" +
                "-- 分析表\n" +
                "ANALYZE task_execution_record;\n" +
                "-- 重建索引\n" +
                "REINDEX INDEX idx_task_execution_time;";
    }

    private String getDefaultCpuOptimizationScript() {
        return "#!/bin/bash\n" +
                "# 设置JVM参数优化\n" +
                "JAVA_OPTS=\"-XX:+UseG1GC -Xms512m -Xmx1024m\"\n" +
                "# 限流配置\n" +
                "rate.limit=1000/sec\n" +
                "# 连接池配置\n" +
                "max.pool.size=20";
    }

    private String getDefaultMemoryOptimizationScript() {
        return "public void processInChunks() {\n" +
                "    int chunkSize = 1000;\n" +
                "    try (Stream<Data> stream = repository.streamAll()) {\n" +
                "        stream.forEach(chunk -> processChunk(chunk));\n" +
                "    }\n" +
                "}";
    }

    private String getDefaultSchedulerCheckScript() {
        return "-- 检查Quartz触发器状态\n" +
                "SELECT TRIGGER_NAME, TRIGGER_STATE\n" +
                "FROM QRTZ_TRIGGERS\n" +
                "WHERE TRIGGER_NAME LIKE '%{taskName}%';\n" +
                "-- 检查任务详情\n" +
                "SELECT JOB_NAME, JOB_GROUP, IS_DURABLE\n" +
                "FROM QRTZ_JOB_DETAILS\n" +
                "WHERE JOB_NAME = '{taskName}';";
    }

    private String getDefaultMonitoringConfig() {
        return "alerts:\n" +
                "  - name: task_health_score\n" +
                "    expr: health_score < 80\n" +
                "    for: 5m\n" +
                "    labels:\n" +
                "      severity: warning\n" +
                "    annotations:\n" +
                "      summary: \"Task {{ $labels.task }} health score low\"\n" +
                "      description: \"Health score is {{ $value }}\"";
    }

    public TaskWeightConfig getDefaultWeightsByImportance(String importance) {
        return switch (importance.toUpperCase()) {
            case "CRITICAL" -> TaskWeightConfig.builder()
                    .durationWeight(0.20)
                    .successRateWeight(0.45)
                    .frequencyWeight(0.20)
                    .resourceWeight(0.15)
                    .build();
            case "HIGH" -> TaskWeightConfig.builder()
                    .durationWeight(0.25)
                    .successRateWeight(0.40)
                    .frequencyWeight(0.20)
                    .resourceWeight(0.15)
                    .build();
            case "MEDIUM" -> TaskWeightConfig.builder()
                    .durationWeight(0.25)
                    .successRateWeight(0.35)
                    .frequencyWeight(0.15)
                    .resourceWeight(0.25)
                    .build();
            default -> TaskWeightConfig.builder()
                    .durationWeight(0.25)
                    .successRateWeight(0.35)
                    .frequencyWeight(0.15)
                    .resourceWeight(0.25)
                    .build();
        };
    }
}
