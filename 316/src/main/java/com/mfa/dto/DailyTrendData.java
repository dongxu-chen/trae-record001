package com.mfa.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DailyTrendData {
    private LocalDate date;
    private Long totalAttempts;
    private Long successCount;
    private Long failureCount;
    private BigDecimal successRate;
}
