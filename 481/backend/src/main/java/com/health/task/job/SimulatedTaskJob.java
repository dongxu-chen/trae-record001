package com.health.task.job;

import com.health.task.entity.TaskExecutionRecord;
import com.health.task.repository.TaskExecutionRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.quartz.Job;
import org.quartz.JobDataMap;
import org.quartz.JobExecutionContext;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Random;

@Component
@RequiredArgsConstructor
@Slf4j
public class SimulatedTaskJob implements Job {

    private final TaskExecutionRecordRepository executionRepo;
    private final Random random = new Random();

    @Override
    public void execute(JobExecutionContext context) {
        JobDataMap dataMap = context.getJobDetail().getJobDataMap();
        String taskName = dataMap.getString("taskName");
        String taskGroup = dataMap.getString("taskGroup");

        LocalDateTime startTime = LocalDateTime.now();

        double baseDuration = getBaseDurationForTask(taskName);
        long duration = (long) (baseDuration + random.nextGaussian() * baseDuration * 0.3);
        duration = Math.max(100, duration);

        boolean success = random.nextDouble() > getFailureRateForTask(taskName);

        double cpuUsage = getBaseCpuForTask(taskName) + random.nextGaussian() * 10;
        cpuUsage = Math.max(5, Math.min(95, cpuUsage));

        double memoryUsage = getBaseMemoryForTask(taskName) + random.nextGaussian() * 50;
        memoryUsage = Math.max(32, Math.min(1024, memoryUsage));

        TaskExecutionRecord record = TaskExecutionRecord.builder()
                .taskName(taskName)
                .taskGroup(taskGroup)
                .cronExpression(dataMap.getString("cronExpression"))
                .startTime(startTime)
                .endTime(startTime.plusNanos(duration * 1_000_000))
                .durationMs(duration)
                .success(success)
                .errorMessage(success ? null : generateErrorMessage(taskName))
                .cpuUsagePercent(cpuUsage)
                .memoryUsageMb(memoryUsage)
                .createdAt(LocalDateTime.now())
                .build();

        executionRepo.save(record);
        log.debug("Simulated execution for task {}: duration={}ms, success={}", taskName, duration, success);
    }

    private double getBaseDurationForTask(String taskName) {
        return switch (taskName) {
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

    private double getFailureRateForTask(String taskName) {
        return switch (taskName) {
            case "DataSyncJob" -> 0.15;
            case "ReportGenerateJob" -> 0.08;
            case "CacheCleanJob" -> 0.02;
            case "EmailNotifyJob" -> 0.05;
            case "LogArchiveJob" -> 0.10;
            case "BackupJob" -> 0.20;
            case "IndexRebuildJob" -> 0.12;
            default -> 0.05;
        };
    }

    private double getBaseCpuForTask(String taskName) {
        return switch (taskName) {
            case "DataSyncJob" -> 45;
            case "ReportGenerateJob" -> 70;
            case "CacheCleanJob" -> 20;
            case "EmailNotifyJob" -> 15;
            case "LogArchiveJob" -> 55;
            case "BackupJob" -> 80;
            case "IndexRebuildJob" -> 85;
            default -> 40;
        };
    }

    private double getBaseMemoryForTask(String taskName) {
        return switch (taskName) {
            case "DataSyncJob" -> 200;
            case "ReportGenerateJob" -> 350;
            case "CacheCleanJob" -> 80;
            case "EmailNotifyJob" -> 120;
            case "LogArchiveJob" -> 250;
            case "BackupJob" -> 500;
            case "IndexRebuildJob" -> 600;
            default -> 200;
        };
    }

    private String generateErrorMessage(String taskName) {
        return switch (taskName) {
            case "DataSyncJob" -> "Connection timeout to remote data source";
            case "ReportGenerateJob" -> "Out of memory during PDF generation";
            case "BackupJob" -> "Disk space insufficient for backup";
            case "IndexRebuildJob" -> "Deadlock detected during index rebuild";
            default -> "Unknown error occurred";
        };
    }
}
