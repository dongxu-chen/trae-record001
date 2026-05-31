package com.datacheck.config;

import com.datacheck.model.CheckTask;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Data
@Component
@ConfigurationProperties(prefix = "check")
public class ThresholdConfig {

    private Map<String, ThresholdSettings> threshold = new HashMap<>();

    private long defaultLatencyThresholdMs = 5000;
    private int defaultBatchSize = 1000;

    @Data
    public static class ThresholdSettings {
        private Long latencyThresholdMs;
        private Integer batchSize;
    }

    public long getLatencyThresholdMs(CheckTask.ImportanceLevel level) {
        if (level == null) {
            return defaultLatencyThresholdMs;
        }
        ThresholdSettings settings = threshold.get(level.name());
        if (settings != null && settings.getLatencyThresholdMs() != null) {
            return settings.getLatencyThresholdMs();
        }
        return defaultLatencyThresholdMs;
    }

    public int getBatchSize(CheckTask.ImportanceLevel level) {
        if (level == null) {
            return defaultBatchSize;
        }
        ThresholdSettings settings = threshold.get(level.name());
        if (settings != null && settings.getBatchSize() != null) {
            return settings.getBatchSize();
        }
        return defaultBatchSize;
    }

    public long getEffectiveLatencyThresholdMs(CheckTask task) {
        if (task.getLatencyThresholdMs() != null) {
            return task.getLatencyThresholdMs();
        }
        return getLatencyThresholdMs(task.getImportanceLevel());
    }

    public int getEffectiveBatchSize(CheckTask task) {
        if (task.getBatchSize() != null) {
            return task.getBatchSize();
        }
        return getBatchSize(task.getImportanceLevel());
    }
}
