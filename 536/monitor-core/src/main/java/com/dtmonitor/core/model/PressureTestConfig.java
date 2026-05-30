package com.dtmonitor.core.model;

import com.dtmonitor.core.enums.TransactionMode;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PressureTestConfig {
    private TransactionMode mode;
    private int concurrency;
    private int durationSeconds;
    private double failureRate;
    private int networkDelayMs;
    private String businessType;
}
