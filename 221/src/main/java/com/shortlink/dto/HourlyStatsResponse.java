package com.shortlink.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
public class HourlyStatsResponse {

    private String shortCode;

    private List<HourlyData> hourlyData = new ArrayList<>();

    private Long totalPv;

    private Long totalUv;

    @Data
    public static class HourlyData {
        private LocalDateTime hour;
        private Long pvCount;

        public HourlyData(LocalDateTime hour, Long pvCount) {
            this.hour = hour;
            this.pvCount = pvCount;
        }
    }
}
