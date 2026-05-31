package com.datacheck.model;

import com.datacheck.model.enums.DataSourceType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CheckTask {
    private String id;

    @NotNull
    private DataSourceType sourceType;

    @NotBlank
    private String tableName;

    private String primaryKey;

    private List<String> compareFields;

    private List<String> excludeFields;

    private String whereCondition;

    private Integer batchSize;

    private Long latencyThresholdMs;

    private Boolean autoRepair;

    private String status;

    private LocalDateTime createdAt;

    private LocalDateTime startedAt;

    private LocalDateTime finishedAt;

    private Boolean stratifiedHashEnabled;

    private Integer stratumCount;

    private ImportanceLevel importanceLevel;

    public enum ImportanceLevel {
        CRITICAL,
        HIGH,
        MEDIUM,
        LOW
    }
}
