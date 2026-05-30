package com.dtmonitor.alert.rule;

import com.dtmonitor.core.enums.AlertLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlertRule {

    private String name;
    private String description;
    private AlertLevel level;
    private String condition;
    private long thresholdMs;
    private boolean enabled;

    public boolean evaluate(long durationMs, String status) {
        if (!enabled) return false;
        switch (condition) {
            case "TIMEOUT":
                return durationMs > thresholdMs;
            case "STATUS_FAILED":
                return "FAILED".equals(status) || "ROLLBACKING".equals(status);
            case "STATUS_ROLLBACK":
                return "ROLLEDBACK".equals(status);
            case "LONG_RUNNING":
                return durationMs > thresholdMs && ("BEGIN".equals(status) || "COMMITTING".equals(status));
            default:
                return false;
        }
    }
}
