package com.datacheck.model;

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
public class GrayReleaseConfig {

    private String id;
    private String name;
    private String description;
    private boolean enabled;
    private GrayStrategy strategy;
    private int currentPhase;
    private List<GrayPhase> phases;
    private Map<String, Object> params;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public enum GrayStrategy {
        PERCENTAGE,
        TABLE_RANGE,
        KEY_RANGE
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class GrayPhase {
        private int phaseIndex;
        private String phaseName;
        private int percentage;
        private List<String> tableNames;
        private String keyRangeStart;
        private String keyRangeEnd;
        private int durationMinutes;
        private boolean autoAdvance;
        private GrayPhaseStatus status;
        private LocalDateTime startedAt;
        private LocalDateTime completedAt;
        private CheckResult phaseResult;
    }

    public enum GrayPhaseStatus {
        PENDING,
        RUNNING,
        COMPLETED,
        FAILED,
        PAUSED
    }

    public int getEffectivePercentage() {
        if (phases == null || phases.isEmpty() || currentPhase >= phases.size()) {
            return 100;
        }
        return phases.get(currentPhase).getPercentage();
    }

    public List<String> getEffectiveTables() {
        if (phases == null || phases.isEmpty() || currentPhase >= phases.size()) {
            return null;
        }
        return phases.get(currentPhase).getTableNames();
    }

    public boolean shouldCheckKey(String key) {
        if (phases == null || phases.isEmpty() || currentPhase >= phases.size()) {
            return true;
        }
        GrayPhase phase = phases.get(currentPhase);
        if (strategy == GrayStrategy.PERCENTAGE) {
            return Math.abs(key.hashCode()) % 100 < phase.getPercentage();
        }
        if (strategy == GrayStrategy.KEY_RANGE) {
            if (phase.getKeyRangeStart() != null && key.compareTo(phase.getKeyRangeStart()) < 0) {
                return false;
            }
            if (phase.getKeyRangeEnd() != null && key.compareTo(phase.getKeyRangeEnd()) > 0) {
                return false;
            }
            return true;
        }
        return true;
    }
}
