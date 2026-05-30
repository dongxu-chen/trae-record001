package com.health.task.config;

import com.health.task.entity.AutoRepairLog;
import com.health.task.entity.HealthScorePrediction;
import com.health.task.entity.OptimizationScript;
import com.health.task.entity.SlaPrediction;
import com.health.task.entity.TaskDependency;
import com.health.task.entity.TaskExecutionRecord;
import com.health.task.entity.TaskWeightConfig;
import com.health.task.repository.AutoRepairLogRepository;
import com.health.task.repository.HealthScorePredictionRepository;
import com.health.task.repository.OptimizationScriptRepository;
import com.health.task.repository.SlaPredictionRepository;
import com.health.task.repository.TaskDependencyRepository;
import com.health.task.repository.TaskExecutionRecordRepository;
import com.health.task.repository.TaskWeightConfigRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

@Component
@RequiredArgsConstructor
@Slf4j
public class DataInitializer implements CommandLineRunner {

    private final TaskExecutionRecordRepository executionRepo;
    private final TaskWeightConfigRepository weightConfigRepo;
    private final TaskDependencyRepository dependencyRepo;
    private final OptimizationScriptRepository scriptRepo;
    private final HealthScorePredictionRepository predictionRepo;
    private final AutoRepairLogRepository autoRepairRepo;
    private final SlaPredictionRepository slaPredictionRepo;
    private final Random random = new Random();

    @Override
    public void run(String... args) {
        if (executionRepo.count() > 0) {
            log.info("Data already exists, skipping initialization");
            return;
        }

        log.info("Initializing sample task execution data...");
        List<TaskExecutionRecord> records = new ArrayList<>();

        String[] taskNames = {"DataSyncJob", "ReportGenerateJob", "CacheCleanJob",
                "EmailNotifyJob", "LogArchiveJob", "BackupJob", "IndexRebuildJob"};

        for (String taskName : taskNames) {
            for (int i = 0; i < 50; i++) {
                double baseDuration = getBaseDuration(taskName);
                long duration = (long) Math.max(100, baseDuration + random.nextGaussian() * baseDuration * 0.3);
                boolean success = random.nextDouble() > getFailureRate(taskName);
                double cpu = Math.max(5, Math.min(95, getBaseCpu(taskName) + random.nextGaussian() * 10));
                double memory = Math.max(32, Math.min(1024, getBaseMemory(taskName) + random.nextGaussian() * 50));

                LocalDateTime execTime = LocalDateTime.now().minusHours(24 - i / 2).minusMinutes(random.nextInt(60));

                records.add(TaskExecutionRecord.builder()
                        .taskName(taskName)
                        .taskGroup("DEFAULT")
                        .cronExpression("0 */5 * * * ?")
                        .startTime(execTime)
                        .endTime(execTime.plusNanos(duration * 1_000_000))
                        .durationMs(duration)
                        .success(success)
                        .errorMessage(success ? null : "Simulated error")
                        .cpuUsagePercent(cpu)
                        .memoryUsageMb(memory)
                        .createdAt(execTime)
                        .build());
            }
        }

        executionRepo.saveAll(records);
        log.info("Initialized {} task execution records", records.size());

        initWeightConfigs();
        initDependencies();
        initOptimizationScripts();
        initPredictions();
        initAutoRepairLogs();
        initSlaPredictions();
    }

    private double getBaseDuration(String task) {
        return switch (task) {
            case "DataSyncJob" -> 3000;
            case "ReportGenerateJob" -> 8000;
            case "CacheCleanJob" -> 1500;
            case "EmailNotifyJob" -> 2000;
            case "LogArchiveJob" -> 6000;
            case "BackupJob" -> 15000;
            case "IndexRebuildJob" -> 12000;
            default -> 4000;
        };
    }

    private double getFailureRate(String task) {
        return switch (task) {
            case "DataSyncJob" -> 0.15;
            case "BackupJob" -> 0.20;
            case "IndexRebuildJob" -> 0.12;
            case "LogArchiveJob" -> 0.10;
            case "ReportGenerateJob" -> 0.08;
            default -> 0.05;
        };
    }

    private double getBaseCpu(String task) {
        return switch (task) {
            case "BackupJob" -> 80;
            case "IndexRebuildJob" -> 85;
            case "ReportGenerateJob" -> 70;
            case "LogArchiveJob" -> 55;
            case "DataSyncJob" -> 45;
            default -> 20;
        };
    }

    private double getBaseMemory(String task) {
        return switch (task) {
            case "IndexRebuildJob" -> 600;
            case "BackupJob" -> 500;
            case "ReportGenerateJob" -> 350;
            case "LogArchiveJob" -> 250;
            case "DataSyncJob" -> 200;
            default -> 100;
        };
    }

    private void initWeightConfigs() {
        if (weightConfigRepo.count() > 0) return;

        weightConfigRepo.save(TaskWeightConfig.builder()
                .taskName("BackupJob")
                .taskGroup("DEFAULT")
                .importanceLevel("CRITICAL")
                .durationWeight(0.20)
                .successRateWeight(0.45)
                .frequencyWeight(0.20)
                .resourceWeight(0.15)
                .description("数据备份任务 - 核心关键业务")
                .build());

        weightConfigRepo.save(TaskWeightConfig.builder()
                .taskName("DataSyncJob")
                .taskGroup("DEFAULT")
                .importanceLevel("HIGH")
                .durationWeight(0.25)
                .successRateWeight(0.40)
                .frequencyWeight(0.20)
                .resourceWeight(0.15)
                .description("数据同步任务 - 高优先级")
                .build());

        weightConfigRepo.save(TaskWeightConfig.builder()
                .taskName("ReportGenerateJob")
                .taskGroup("DEFAULT")
                .importanceLevel("HIGH")
                .durationWeight(0.25)
                .successRateWeight(0.40)
                .frequencyWeight(0.20)
                .resourceWeight(0.15)
                .description("报表生成任务 - 高优先级")
                .build());

        weightConfigRepo.save(TaskWeightConfig.builder()
                .taskName("IndexRebuildJob")
                .taskGroup("DEFAULT")
                .importanceLevel("MEDIUM")
                .durationWeight(0.25)
                .successRateWeight(0.35)
                .frequencyWeight(0.15)
                .resourceWeight(0.25)
                .description("索引重建任务 - 中等优先级")
                .build());

        weightConfigRepo.save(TaskWeightConfig.builder()
                .taskName("LogArchiveJob")
                .taskGroup("DEFAULT")
                .importanceLevel("MEDIUM")
                .durationWeight(0.25)
                .successRateWeight(0.35)
                .frequencyWeight(0.15)
                .resourceWeight(0.25)
                .description("日志归档任务 - 中等优先级")
                .build());

        weightConfigRepo.save(TaskWeightConfig.builder()
                .taskName("EmailNotifyJob")
                .taskGroup("DEFAULT")
                .importanceLevel("LOW")
                .durationWeight(0.25)
                .successRateWeight(0.35)
                .frequencyWeight(0.15)
                .resourceWeight(0.25)
                .description("邮件通知任务 - 低优先级")
                .build());

        weightConfigRepo.save(TaskWeightConfig.builder()
                .taskName("CacheCleanJob")
                .taskGroup("DEFAULT")
                .importanceLevel("LOW")
                .durationWeight(0.25)
                .successRateWeight(0.35)
                .frequencyWeight(0.15)
                .resourceWeight(0.25)
                .description("缓存清理任务 - 低优先级")
                .build());

        log.info("Initialized weight configurations for all tasks");
    }

    private void initDependencies() {
        if (dependencyRepo.count() > 0) return;

        dependencyRepo.save(TaskDependency.builder()
                .taskName("ReportGenerateJob")
                .upstreamTaskName("DataSyncJob")
                .dependencyType("DATA")
                .maxWaitSeconds(60)
                .description("报表生成依赖数据同步完成")
                .build());

        dependencyRepo.save(TaskDependency.builder()
                .taskName("IndexRebuildJob")
                .upstreamTaskName("DataSyncJob")
                .dependencyType("DATA")
                .maxWaitSeconds(120)
                .description("索引重建依赖数据同步完成")
                .build());

        dependencyRepo.save(TaskDependency.builder()
                .taskName("BackupJob")
                .upstreamTaskName("LogArchiveJob")
                .dependencyType("SEQUENTIAL")
                .maxWaitSeconds(300)
                .description("备份在日志归档之后执行")
                .build());

        dependencyRepo.save(TaskDependency.builder()
                .taskName("EmailNotifyJob")
                .upstreamTaskName("ReportGenerateJob")
                .dependencyType("DATA")
                .maxWaitSeconds(30)
                .description("邮件通知依赖报表生成完成")
                .build());

        log.info("Initialized task dependency configurations");
    }

    private void initOptimizationScripts() {
        if (scriptRepo.count() > 0) return;

        scriptRepo.save(OptimizationScript.builder()
                .issueCategory("LOW_SUCCESS_RATE")
                .scriptType("JAVA")
                .scriptName("RetryAndCircuitBreaker.java")
                .description("Spring Retry 和 Resilience4j 熔断保护")
                .scriptContent("""
                        import org.springframework.retry.annotation.Retryable;
                        import org.springframework.retry.annotation.Backoff;
                        import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
                        
                        @Service
                        public class RetryableTaskService {
                            
                            @Retryable(
                                maxAttempts = 3,
                                backoff = @Backoff(delay = 1000, multiplier = 2, maxDelay = 5000)
                            )
                            @CircuitBreaker(
                                name = "taskCircuitBreaker",
                                fallbackMethod = "handleFallback"
                            )
                            public void executeWithRetry(String taskName) {
                                // 任务执行逻辑
                                taskExecutor.execute(taskName);
                            }
                            
                            private void handleFallback(String taskName, Exception e) {
                                log.error("Task {} failed after retries: {}", taskName, e.getMessage());
                                // 降级处理逻辑
                            }
                        }
                        """)
                .executionCommand("1. 添加依赖: spring-retry, resilience4j\n2. 配置重试和熔断参数\n3. 在任务类上添加注解")
                .riskLevel("MEDIUM")
                .build());

        scriptRepo.save(OptimizationScript.builder()
                .issueCategory("HIGH_DURATION")
                .scriptType("SQL")
                .scriptName("optimize_queries.sql")
                .description("SQL查询优化脚本")
                .scriptContent("""
                        -- 1. 分析慢查询
                        EXPLAIN ANALYZE SELECT * FROM task_execution_record WHERE task_name = ?;
                        
                        -- 2. 创建索引
                        CREATE INDEX IF NOT EXISTS idx_task_execution_compound 
                        ON task_execution_record(task_name, created_at DESC, success);
                        
                        -- 3. 分析表
                        ANALYZE task_execution_record;
                        
                        -- 4. 定期重建索引
                        REINDEX INDEX idx_task_execution_compound;
                        
                        -- 5. 检查锁等待
                        SELECT pid, now() - query_start as duration, query 
                        FROM pg_stat_activity 
                        WHERE state = 'active' 
                        AND now() - query_start > interval '5 minutes';
                        """)
                .executionCommand("1. 执行 EXPLAIN ANALYZE 分析慢查询\n2. 创建必要的索引\n3. 定期执行 ANALYZE 更新统计信息")
                .riskLevel("LOW")
                .build());

        scriptRepo.save(OptimizationScript.builder()
                .issueCategory("HIGH_CPU")
                .scriptType("SHELL")
                .scriptName("optimize_cpu.sh")
                .description("CPU优化和限流配置脚本")
                .scriptContent("""
                        #!/bin/bash
                        # CPU 优化脚本
                        
                        # 1. JVM 参数优化
                        export JAVA_OPTS="-XX:+UseG1GC \
                          -XX:MaxGCPauseMillis=200 \
                          -XX:ParallelGCThreads=4 \
                          -Xms512m -Xmx1024m \
                          -XX:+HeapDumpOnOutOfMemoryError"
                        
                        # 2. 限流配置（使用Resilience4j RateLimiter）
                        echo "rateLimiter:
                          instances:
                            taskRateLimiter:
                              limitForPeriod: 1000
                              limitRefreshPeriod: 1s
                              timeoutDuration: 500ms" > application-rate.yml
                        
                        # 3. 连接池配置
                        echo "spring:
                          datasource:
                            hikari:
                              maximum-pool-size: 20
                              minimum-idle: 5
                              connection-timeout: 30000
                              idle-timeout: 600000" > application-pool.yml
                        
                        echo "CPU optimization config created successfully"
                        """)
                .executionCommand("chmod +x optimize_cpu.sh && ./optimize_cpu.sh")
                .riskLevel("MEDIUM")
                .build());

        scriptRepo.save(OptimizationScript.builder()
                .issueCategory("HIGH_MEMORY")
                .scriptType("JAVA")
                .scriptName("StreamProcessor.java")
                .description("流式处理减少内存占用")
                .scriptContent("""
                        import org.springframework.data.domain.Page;
                        import org.springframework.data.domain.PageRequest;
                        import java.util.stream.Stream;
                        
                        @Service
                        public class StreamProcessor {
                            
                            private static final int CHUNK_SIZE = 1000;
                            
                            public void processLargeDataset() {
                                // 使用 Stream 流式处理
                                try (Stream<DataRecord> stream = dataRepository.streamAll()) {
                                    stream.forEach(this::processRecord);
                                }
                            }
                            
                            // 使用分页批处理
                            public void processInChunks() {
                                int page = 0;
                                Page<DataRecord> recordPage;
                                do {
                                    recordPage = dataRepository.findAll(
                                        PageRequest.of(page, CHUNK_SIZE)
                                    );
                                    recordPage.getContent().forEach(this::processRecord);
                                    // 清除一级缓存
                                    entityManager.flush();
                                    entityManager.clear();
                                    page++;
                                } while (page < recordPage.getTotalPages());
                            }
                            
                            private void processRecord(DataRecord record) {
                                // 单条记录处理逻辑
                            }
                        }
                        """)
                .executionCommand("1. 将结果集改为流式处理\n2. 添加分页处理逻辑\n3. 定期清除实体管理器缓存")
                .riskLevel("MEDIUM")
                .build());

        scriptRepo.save(OptimizationScript.builder()
                .issueCategory("NO_EXECUTION")
                .scriptType("SQL")
                .scriptName("check_scheduler.sql")
                .description("检查调度器状态的SQL")
                .scriptContent("""
                        -- 1. 检查触发器状态
                        SELECT 
                            TRIGGER_NAME,
                            TRIGGER_GROUP,
                            TRIGGER_STATE,
                            NEXT_FIRE_TIME,
                            PREV_FIRE_TIME
                        FROM QRTZ_TRIGGERS
                        WHERE TRIGGER_NAME LIKE '%{taskName}%';
                        
                        -- 2. 检查任务详情
                        SELECT 
                            JOB_NAME,
                            JOB_GROUP,
                            IS_DURABLE,
                            IS_NONCONCURRENT,
                            IS_UPDATE_DATA
                        FROM QRTZ_JOB_DETAILS
                        WHERE JOB_NAME = '{taskName}';
                        
                        -- 3. 检查暂停的触发器
                        SELECT TRIGGER_NAME, TRIGGER_GROUP 
                        FROM QRTZ_PAUSED_TRIGGER_GRPS;
                        
                        -- 4. 检查调度器元数据
                        SELECT 
                            SCHED_NAME,
                            INSTANCE_NAME,
                            LAST_CHECKIN_TIME,
                            CHECKIN_INTERVAL
                        FROM QRTZ_SCHEDULER_STATE;
                        """)
                .executionCommand("1. 检查Quartz配置类中的任务定义\n2. 确认触发器状态为 WAITING\n3. 查看调度器日志确认任务已启动")
                .riskLevel("HIGH")
                .build());

        log.info("Initialized optimization script templates");
    }

    private void initPredictions() {
        log.info("Initializing sample prediction data...");

        String[] taskNames = {"DataSyncJob", "ReportGenerateJob", "CacheCleanJob",
                "EmailNotifyJob", "LogArchiveJob", "BackupJob", "IndexRebuildJob"};
        LocalDateTime now = LocalDateTime.now();

        for (String taskName : taskNames) {
            String importance = getTaskImportance(taskName);
            int baseScore = getBaseScore(taskName);
            String trend = random.nextDouble() > 0.4 ? "STABLE" : random.nextDouble() > 0.5 ? "IMPROVING" : "DECLINING";
            double slope = trend.equals("IMPROVING") ? random.nextDouble() * 2 :
                    trend.equals("DECLINING") ? -random.nextDouble() * 2 : random.nextDouble() - 0.5;

            for (int i = 1; i <= 4; i++) {
                int horizonHours = i * 6;
                LocalDateTime targetTime = now.plusHours(horizonHours);
                int predictedScore = (int) Math.max(0, Math.min(100,
                        baseScore + slope * i * 10 + random.nextGaussian() * 5));
                double confidence = Math.max(0.5, 0.9 - i * 0.1);
                int stdDev = (int) (5 + random.nextDouble() * 8);

                predictionRepo.save(HealthScorePrediction.builder()
                        .taskName(taskName)
                        .taskGroup("DEFAULT")
                        .predictedScore(predictedScore)
                        .confidence(confidence)
                        .trendDirection(trend)
                        .trendSlope(slope)
                        .predictionTime(now)
                        .targetTime(targetTime)
                        .predictionHorizonHours(horizonHours)
                        .algorithmUsed("LINEAR_REGRESSION_WITH_METRICS_ADJUSTMENT")
                        .predictionDetails(String.format(
                                "Based on last 30 historical scores; trend: %s; adjusted by task importance: %s",
                                trend, importance))
                        .lowerBound(Math.max(0, predictedScore - stdDev))
                        .upperBound(Math.min(100, predictedScore + stdDev))
                        .build());
            }
        }

        log.info("Initialized prediction data for {} tasks", taskNames.length);
    }

    private void initAutoRepairLogs() {
        log.info("Initializing sample auto-repair log data...");

        LocalDateTime now = LocalDateTime.now();

        autoRepairRepo.save(AutoRepairLog.builder()
                .taskName("DataSyncJob")
                .taskGroup("DEFAULT")
                .failureType("LOW_SUCCESS_RATE")
                .repairAction("INCREASE_RETRY_PARAMETERS")
                .oldValue("retries=3, delay=1000ms")
                .newValue("retries=5, delay=1500ms")
                .repairTime(now.minusDays(2))
                .status("SUCCESS")
                .repairDetails("Success rate was 82%. Increased max retries from 3 to 5 and retry delay from 1000ms to 1500ms with exponential backoff.")
                .maxRetriesBefore(3)
                .maxRetriesAfter(5)
                .retryDelayMsBefore(1000L)
                .retryDelayMsAfter(1500L)
                .successRateAfterRepair(91.5)
                .followUpScore(78)
                .riskLevel("MEDIUM")
                .build());

        autoRepairRepo.save(AutoRepairLog.builder()
                .taskName("ReportGenerateJob")
                .taskGroup("DEFAULT")
                .failureType("HIGH_DURATION")
                .repairAction("INCREASE_TIMEOUT")
                .oldValue("30000ms")
                .newValue("39000ms")
                .repairTime(now.minusDays(1))
                .status("SUCCESS")
                .repairDetails("Average execution duration was 18000ms, peaking at 35000ms. Increased timeout to prevent premature timeout failures.")
                .timeoutMsBefore(30000L)
                .timeoutMsAfter(39000L)
                .successRateAfterRepair(94.0)
                .followUpScore(82)
                .riskLevel("LOW")
                .build());

        autoRepairRepo.save(AutoRepairLog.builder()
                .taskName("BackupJob")
                .taskGroup("DEFAULT")
                .failureType("HIGH_VARIANCE")
                .repairAction("INCREASE_RETRY_AND_DELAY")
                .oldValue("retries=3, delay=1000ms")
                .newValue("retries=4, delay=2000ms")
                .repairTime(now.minusHours(8))
                .status("PENDING")
                .repairDetails("High execution variance detected in backup job. Increased retry attempts and delay to handle inconsistent performance.")
                .maxRetriesBefore(3)
                .maxRetriesAfter(4)
                .retryDelayMsBefore(1000L)
                .retryDelayMsAfter(2000L)
                .riskLevel("MEDIUM")
                .build());

        autoRepairRepo.save(AutoRepairLog.builder()
                .taskName("EmailNotifyJob")
                .taskGroup("DEFAULT")
                .failureType("LOW_SUCCESS_RATE")
                .repairAction("INCREASE_RETRY_PARAMETERS")
                .oldValue("retries=2, delay=500ms")
                .newValue("retries=4, delay=1000ms")
                .repairTime(now.minusHours(36))
                .status("SUCCESS")
                .repairDetails("Email notification failures due to SMTP server timeouts. Increased retries and delays.")
                .maxRetriesBefore(2)
                .maxRetriesAfter(4)
                .retryDelayMsBefore(500L)
                .retryDelayMsAfter(1000L)
                .successRateAfterRepair(96.2)
                .followUpScore(88)
                .riskLevel("LOW")
                .build());

        log.info("Initialized {} auto-repair log entries", 4);
    }

    private void initSlaPredictions() {
        log.info("Initializing sample SLA prediction data...");

        String[] taskNames = {"DataSyncJob", "ReportGenerateJob", "BackupJob", "EmailNotifyJob"};
        LocalDateTime now = LocalDateTime.now();
        LocalDate today = now.toLocalDate();
        LocalDateTime monthStart = today.withDayOfMonth(1).atStartOfDay();
        LocalDateTime monthEnd = today.withDayOfMonth(today.lengthOfMonth()).atTime(23, 59, 59);

        int daysAnalyzed = today.getDayOfMonth();
        int daysRemaining = today.lengthOfMonth() - daysAnalyzed;

        slaPredictionRepo.save(SlaPrediction.builder()
                .taskName("BackupJob")
                .taskGroup("DEFAULT")
                .slaTargetScore(80)
                .predictedMonthlyScore(87.3)
                .currentMonthlyAvg(85.0)
                .achievementProbability(0.78)
                .daysRemainingInMonth(daysRemaining)
                .daysAnalyzed(daysAnalyzed)
                .currentSuccessRate(91.5)
                .requiredSuccessRate(93.2)
                .predictedFailuresRemaining(3)
                .slaStatus("AT_RISK")
                .recommendations("SLA achievement is at risk. Current avg: 85.0, target: 80. Need to improve success rate to at least 93%.")
                .predictionTime(now)
                .monthStart(monthStart)
                .monthEnd(monthEnd)
                .bestCaseScore(92.0)
                .worstCaseScore(78.0)
                .healthyDays(12)
                .warningDays(5)
                .criticalDays(2)
                .build());

        slaPredictionRepo.save(SlaPrediction.builder()
                .taskName("DataSyncJob")
                .taskGroup("DEFAULT")
                .slaTargetScore(80)
                .predictedMonthlyScore(91.2)
                .currentMonthlyAvg(89.5)
                .achievementProbability(0.92)
                .daysRemainingInMonth(daysRemaining)
                .daysAnalyzed(daysAnalyzed)
                .currentSuccessRate(94.8)
                .requiredSuccessRate(91.0)
                .predictedFailuresRemaining(1)
                .slaStatus("ON_TRACK")
                .recommendations("SLA achievement is on track. Continue monitoring for regressions.")
                .predictionTime(now)
                .monthStart(monthStart)
                .monthEnd(monthEnd)
                .bestCaseScore(94.0)
                .worstCaseScore(86.0)
                .healthyDays(15)
                .warningDays(3)
                .criticalDays(1)
                .build());

        slaPredictionRepo.save(SlaPrediction.builder()
                .taskName("ReportGenerateJob")
                .taskGroup("DEFAULT")
                .slaTargetScore(80)
                .predictedMonthlyScore(76.8)
                .currentMonthlyAvg(74.0)
                .achievementProbability(0.35)
                .daysRemainingInMonth(daysRemaining)
                .daysAnalyzed(daysAnalyzed)
                .currentSuccessRate(86.2)
                .requiredSuccessRate(97.5)
                .predictedFailuresRemaining(5)
                .slaStatus("WARNING")
                .recommendations("SLA achievement is in danger. Immediate action required to prevent SLA breach.")
                .predictionTime(now)
                .monthStart(monthStart)
                .monthEnd(monthEnd)
                .bestCaseScore(84.0)
                .worstCaseScore(68.0)
                .healthyDays(8)
                .warningDays(6)
                .criticalDays(5)
                .build());

        log.info("Initialized SLA prediction data for {} tasks", 3);
    }

    private String getTaskImportance(String task) {
        return switch (task) {
            case "BackupJob" -> "CRITICAL";
            case "DataSyncJob" -> "HIGH";
            case "ReportGenerateJob" -> "HIGH";
            default -> "MEDIUM";
        };
    }

    private int getBaseScore(String task) {
        return switch (task) {
            case "BackupJob" -> 75;
            case "DataSyncJob" -> 88;
            case "ReportGenerateJob" -> 72;
            case "EmailNotifyJob" -> 82;
            default -> 85;
        };
    }
}
