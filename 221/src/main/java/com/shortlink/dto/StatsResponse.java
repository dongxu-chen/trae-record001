package com.shortlink.dto;

import lombok.Data;

import java.time.LocalDate;
import java.util.Map;

@Data
public class StatsResponse {

    private String shortCode;

    private Long totalPv;

    private Long totalUv;

    private Map<String, Long> deviceStats;

    private Map<String, Long> browserStats;

    private Map<String, Long> regionStats;

    private Map<LocalDate, Long> dailyStats;
}
