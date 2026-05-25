package com.alert.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class ReportDTO {

    private String timeRange;
    private Long totalAlerts;
    private Long resolvedAlerts;
    private Double avgMttrMinutes;
    private Map<String, Long> alertBySeverity;
    private Map<String, Long> alertByStatus;
    private Map<String, Long> alertBySource;
    private List<DailyTrend> dailyTrend;
    private List<HourlyTrend> hourlyTrend;
    private List<String> topHosts;
    private List<String> topServices;
    private List<RootCauseSummary> rootCauseAnalysis;
    private Double slaCompliance;

    @Data
    public static class DailyTrend {
        private String date;
        private Long count;
        private Long resolved;
    }

    @Data
    public static class HourlyTrend {
        private Integer hour;
        private Double avgCount;
    }

    @Data
    public static class RootCauseSummary {
        private String rootCause;
        private Long count;
        private Double avgMttr;
    }
}
