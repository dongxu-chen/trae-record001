package com.medical.stockwarning.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Data
@Builder
public class TrendForecastDTO {

    private Long medicineId;
    private String medicineName;
    private String medicineCode;
    private LocalDate forecastStartDate;
    private LocalDate forecastEndDate;
    private Integer forecastDays;
    private List<DailyForecast> dailyForecasts;
    private BigDecimal totalForecastedQuantity;
    private BigDecimal averageDailyDemand;
    private BigDecimal peakDailyDemand;
    private LocalDate peakDate;
    private Boolean isSeasonal;
    private String seasonPattern;
    private BigDecimal seasonalFactor;
    private Double trendSlope;
    private String trendDirection;
    private Double confidenceLevel;

    @Data
    @Builder
    public static class DailyForecast {
        private LocalDate date;
        private BigDecimal forecastedQuantity;
        private BigDecimal lowerBound;
        private BigDecimal upperBound;
        private String seasonTag;
    }
}
