package com.dtmonitor.core.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PressureTestMetrics {
    private long totalRequests;
    private long successCount;
    private long failureCount;
    private long timeoutCount;
    private double avgResponseTimeMs;
    private double p95ResponseTimeMs;
    private double p99ResponseTimeMs;
    private double tps;
    private long rollbackCount;
    private LocalDateTime timestamp;
}
