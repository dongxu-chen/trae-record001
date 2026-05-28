package com.dbpool.optimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SlowSqlAnalysis {
    private int totalSlowQueries;
    private double avgSlowQueryTimeMs;
    private double maxSlowQueryTimeMs;
    private double avgBorrowTimeForSlowMs;
    private double avgHoldTimeForSlowMs;
    private double correlationWithPoolPressure;
    private double leakRiskScore;
    private String leakRiskLevel;
    private List<SlowSqlRecord> topSlowQueries;
    private Map<String, Integer> slowQueryTypeDistribution;
    private Map<Integer, Integer> slowQueryByHour;
    private List<String> analysisSummary;
    private List<ConnectionLeakAlert> activeAlerts;
}
