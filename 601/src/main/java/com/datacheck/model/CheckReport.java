package com.datacheck.model;

import com.datacheck.model.enums.DataSourceType;
import com.datacheck.model.enums.DiffType;
import com.datacheck.model.enums.RepairStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CheckReport {

    private String id;
    private String taskId;
    private DataSourceType sourceType;
    private String tableName;
    private CheckTask.ImportanceLevel importanceLevel;
    private String checkMode;
    private LocalDateTime generatedAt;

    private SummarySection summary;
    private DiffStatistics diffStatistics;
    private RepairStatistics repairStatistics;
    private List<DiffDetail> diffDetails;
    private List<RepairRecord> repairRecords;
    private TrendAnalysis trendAnalysis;
    private Map<String, Object> metadata;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SummarySection {
        private long totalSourceRecords;
        private long totalTargetRecords;
        private long totalDiffs;
        private long totalRepaired;
        private long totalPendingRepair;
        private long totalFailedRepair;
        private double repairRate;
        private double diffRate;
        private double avgLatencyMs;
        private double maxLatencyMs;
        private long durationMs;
        private long hashVerifiedRecords;
        private long hashSkippedRecords;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DiffStatistics {
        private long missingInTargetCount;
        private long missingInSourceCount;
        private long valueMismatchCount;
        private long latencyExceededCount;
        private Map<String, Long> diffByTable;
        private Map<String, Long> diffByHour;
        private List<TopDiffField> topDiffFields;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TopDiffField {
        private String fieldName;
        private long count;
        private double percentage;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DiffDetail {
        private String diffId;
        private String key;
        private DiffType diffType;
        private Map<String, Object> diffFields;
        private long latencyMs;
        private LocalDateTime detectedAt;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RepairRecord {
        private String diffId;
        private String key;
        private DiffType diffType;
        private RepairStatus repairStatus;
        private int repairAttempts;
        private String repairErrorMessage;
        private LocalDateTime repairedAt;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RepairStatistics {
        private long totalRepairs;
        private long successCount;
        private long failedCount;
        private double successRate;
        private Map<DiffType, Long> repairByType;
        private Map<RepairStatus, Long> repairByStatus;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TrendAnalysis {
        private double diffTrendRate;
        private double latencyTrendRate;
        private double repairTrendRate;
        private String diffTrendDirection;
        private String latencyTrendDirection;
        private LocalDateTime nextCheckSuggestion;
        private double predictedDiffCount;
        private double predictedAvgLatency;
        private String riskLevel;
        private String recommendation;
    }
}
