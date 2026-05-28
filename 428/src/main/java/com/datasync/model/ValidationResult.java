package com.datasync.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ValidationResult implements Serializable {

    private static final long serialVersionUID = 1L;

    private String sourceSchema;
    private String sourceTable;
    private String targetDatabase;
    private String targetTable;
    private long validationTime;
    private long durationMs;
    private ValidationStatus status;
    private long sourceRowCount;
    private long targetRowCount;
    private long diffCount;
    private long matchCount;
    private List<RowDiff> rowDiffs = new ArrayList<>();
    private String errorMessage;

    public enum ValidationStatus {
        SUCCESS,
        FAILED,
        WARNING,
        ERROR
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RowDiff implements Serializable {
        private static final long serialVersionUID = 1L;
        private String primaryKey;
        private DiffType diffType;
        private Map<String, Object> sourceRow;
        private Map<String, Object> targetRow;
        private List<ColumnDiff> columnDiffs = new ArrayList<>();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ColumnDiff implements Serializable {
        private static final long serialVersionUID = 1L;
        private String columnName;
        private Object sourceValue;
        private Object targetValue;
        private String sourceType;
        private String targetType;
    }

    public enum DiffType {
        SOURCE_ONLY,
        TARGET_ONLY,
        VALUE_MISMATCH
    }

    public double getMatchRate() {
        if (sourceRowCount == 0) {
            return 100.0;
        }
        return (double) matchCount / sourceRowCount * 100.0;
    }

    public boolean isConsistent() {
        return diffCount == 0 && sourceRowCount == targetRowCount;
    }
}
