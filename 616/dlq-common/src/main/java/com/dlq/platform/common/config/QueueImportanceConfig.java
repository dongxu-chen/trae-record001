package com.dlq.platform.common.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.HashMap;
import java.util.Map;

@Data
@Configuration
@ConfigurationProperties(prefix = "dlq.queue")
public class QueueImportanceConfig {

    private Map<String, QueueThreshold> thresholds = new HashMap<>();

    private QueueThreshold defaultThreshold = QueueThreshold.builder()
            .importanceLevel(ImportanceLevel.NORMAL)
            .maxRetryCount(5)
            .autoArchiveDays(7)
            .alertEnabled(true)
            .alertSilenceMinutes(30)
            .alertThreshold(10)
            .replayEnabled(true)
            .autoReplayEnabled(false)
            .maxAutoReplayCount(3)
            .build();

    @Data
    public static class QueueThreshold {
        private ImportanceLevel importanceLevel;
        private Integer maxRetryCount;
        private Integer autoArchiveDays;
        private Boolean alertEnabled;
        private Integer alertSilenceMinutes;
        private Integer alertThreshold;
        private Boolean replayEnabled;
        private Boolean autoReplayEnabled;
        private Integer maxAutoReplayCount;
        private String description;

        public static QueueThresholdBuilder builder() {
            return new QueueThresholdBuilder();
        }

        public static class QueueThresholdBuilder {
            private ImportanceLevel importanceLevel;
            private Integer maxRetryCount;
            private Integer autoArchiveDays;
            private Boolean alertEnabled;
            private Integer alertSilenceMinutes;
            private Integer alertThreshold;
            private Boolean replayEnabled;
            private Boolean autoReplayEnabled;
            private Integer maxAutoReplayCount;
            private String description;

            public QueueThresholdBuilder importanceLevel(ImportanceLevel importanceLevel) {
                this.importanceLevel = importanceLevel;
                return this;
            }

            public QueueThresholdBuilder maxRetryCount(Integer maxRetryCount) {
                this.maxRetryCount = maxRetryCount;
                return this;
            }

            public QueueThresholdBuilder autoArchiveDays(Integer autoArchiveDays) {
                this.autoArchiveDays = autoArchiveDays;
                return this;
            }

            public QueueThresholdBuilder alertEnabled(Boolean alertEnabled) {
                this.alertEnabled = alertEnabled;
                return this;
            }

            public QueueThresholdBuilder alertSilenceMinutes(Integer alertSilenceMinutes) {
                this.alertSilenceMinutes = alertSilenceMinutes;
                return this;
            }

            public QueueThresholdBuilder alertThreshold(Integer alertThreshold) {
                this.alertThreshold = alertThreshold;
                return this;
            }

            public QueueThresholdBuilder replayEnabled(Boolean replayEnabled) {
                this.replayEnabled = replayEnabled;
                return this;
            }

            public QueueThresholdBuilder autoReplayEnabled(Boolean autoReplayEnabled) {
                this.autoReplayEnabled = autoReplayEnabled;
                return this;
            }

            public QueueThresholdBuilder maxAutoReplayCount(Integer maxAutoReplayCount) {
                this.maxAutoReplayCount = maxAutoReplayCount;
                return this;
            }

            public QueueThresholdBuilder description(String description) {
                this.description = description;
                return this;
            }

            public QueueThreshold build() {
                QueueThreshold threshold = new QueueThreshold();
                threshold.setImportanceLevel(importanceLevel);
                threshold.setMaxRetryCount(maxRetryCount);
                threshold.setAutoArchiveDays(autoArchiveDays);
                threshold.setAlertEnabled(alertEnabled);
                threshold.setAlertSilenceMinutes(alertSilenceMinutes);
                threshold.setAlertThreshold(alertThreshold);
                threshold.setReplayEnabled(replayEnabled);
                threshold.setAutoReplayEnabled(autoReplayEnabled);
                threshold.setMaxAutoReplayCount(maxAutoReplayCount);
                threshold.setDescription(description);
                return threshold;
            }
        }
    }

    public enum ImportanceLevel {
        CORE("核心队列", "最严格的阈值配置，立即告警，限制重放次数"),
        HIGH("高优先级队列", "严格的阈值配置，快速告警"),
        NORMAL("普通队列", "标准阈值配置"),
        LOW("低优先级队列", "宽松的阈值配置，延迟告警");

        private final String label;
        private final String description;

        ImportanceLevel(String label, String description) {
            this.label = label;
            this.description = description;
        }

        public String getLabel() { return label; }
        public String getDescription() { return description; }
    }

    public QueueThreshold getQueueThreshold(String topicOrQueue) {
        QueueThreshold threshold = thresholds.get(topicOrQueue);
        if (threshold == null) {
            for (Map.Entry<String, QueueThreshold> entry : thresholds.entrySet()) {
                if (topicOrQueue.contains(entry.getKey()) || topicOrQueue.matches(entry.getKey())) {
                    threshold = entry.getValue();
                    break;
                }
            }
        }
        return threshold != null ? threshold : defaultThreshold;
    }

    public boolean shouldAlert(String topicOrQueue, int currentCount) {
        QueueThreshold threshold = getQueueThreshold(topicOrQueue);
        if (!Boolean.TRUE.equals(threshold.getAlertEnabled())) {
            return false;
        }
        return currentCount >= threshold.getAlertThreshold();
    }

    public boolean canRetry(String topicOrQueue, int currentRetryCount) {
        QueueThreshold threshold = getQueueThreshold(topicOrQueue);
        return currentRetryCount < threshold.getMaxRetryCount();
    }

    public boolean shouldAutoArchive(String topicOrQueue, int daysOld) {
        QueueThreshold threshold = getQueueThreshold(topicOrQueue);
        return daysOld >= threshold.getAutoArchiveDays();
    }

    public boolean canReplay(String topicOrQueue) {
        QueueThreshold threshold = getQueueThreshold(topicOrQueue);
        return Boolean.TRUE.equals(threshold.getReplayEnabled());
    }

    public boolean shouldAutoReplay(String topicOrQueue, int currentRetryCount) {
        QueueThreshold threshold = getQueueThreshold(topicOrQueue);
        if (!Boolean.TRUE.equals(threshold.getAutoReplayEnabled())) {
            return false;
        }
        return currentRetryCount < threshold.getMaxAutoReplayCount();
    }
}
