package com.datasync.validator;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DataValidationResult implements Serializable {
    private static final long serialVersionUID = 1L;

    private String validationId;
    private String sourceDatacenterId;
    private String targetDatacenterId;
    private String tableName;
    private long sampleSize;
    private long matchCount;
    private long mismatchCount;
    private long missingCount;
    private double matchRate;
    private boolean success;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private long durationMs;
    private List<MismatchDetail> mismatchDetails;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MismatchDetail implements Serializable {
        private String primaryKey;
        private String columnName;
        private Object sourceValue;
        private Object targetValue;
        private String mismatchType;
    }
}
