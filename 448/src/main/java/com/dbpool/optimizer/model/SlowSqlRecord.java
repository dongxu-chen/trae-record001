package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SlowSqlRecord {
    private long timestamp;
    private String sqlId;
    private String sqlType;
    private String sqlPreview;
    private double executionTimeMs;
    private double borrowTimeMs;
    private double holdTimeMs;
    private double waitTimeMs;
    private int connectionId;
    private boolean isLongTransaction;
    private boolean isPotentialLeak;
    private String threadName;
    private String stackTraceHint;
}
