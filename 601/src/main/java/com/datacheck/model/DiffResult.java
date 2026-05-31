package com.datacheck.model;

import com.datacheck.model.enums.DataSourceType;
import com.datacheck.model.enums.DiffType;
import com.datacheck.model.enums.RepairStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DiffResult {
    private String id;
    private String key;
    private DiffType diffType;
    private DataSourceType sourceType;
    private String tableName;
    private Map<String, Object> sourceData;
    private Map<String, Object> targetData;
    private Map<String, Object> diffFields;
    private long latencyMs;
    private LocalDateTime detectedAt;
    private RepairStatus repairStatus;
    private int repairAttempts;
    private String repairErrorMessage;
}
