package com.dtmonitor.core.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PressureTestResult {
    private String testId;
    private PressureTestConfig config;
    private TestStatus status;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    @Builder.Default
    private List<PressureTestMetrics> metrics = new ArrayList<>();
    private PressureTestMetrics summary;

    public enum TestStatus {
        RUNNING,
        COMPLETED,
        FAILED,
        CANCELLED
    }
}
