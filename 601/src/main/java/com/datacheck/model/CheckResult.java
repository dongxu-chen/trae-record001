package com.datacheck.model;

import com.datacheck.model.enums.DataSourceType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CheckResult {
    private String taskId;
    private DataSourceType sourceType;
    private String tableName;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private long totalSourceRecords;
    private long totalTargetRecords;
    private long diffCount;
    private long latencyCount;
    private double avgLatencyMs;
    private double maxLatencyMs;
    private List<DiffResult> diffs;
    private Map<String, Object> metrics = new ConcurrentHashMap<>();
    private String checkMode;
}
