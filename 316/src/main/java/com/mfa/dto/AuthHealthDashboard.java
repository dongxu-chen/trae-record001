package com.mfa.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuthHealthDashboard {
    private Long totalUsers;
    private Long activeUsersToday;
    private Long totalAttemptsToday;
    private Long successCountToday;
    private Long failureCountToday;
    private BigDecimal overallSuccessRate;
    private List<AuthMethodStats> methodStats;
    private List<DailyTrendData> dailyTrends;
    private Map<String, Long> riskLevelDistribution;
    private Map<String, Long> failureReasons;
    private BigDecimal avgAuthenticationTimeMs;
    private LocalDate reportDate;
}
