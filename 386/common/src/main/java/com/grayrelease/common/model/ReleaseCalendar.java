package com.grayrelease.common.model;

import com.grayrelease.common.enums.ReleaseWindowStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReleaseCalendar {

    private String id;

    private String serviceName;

    private String name;

    private String description;

    private ReleaseWindowStatus status;

    private LocalDate startDate;

    private LocalDate endDate;

    private LocalTime startTime;

    private LocalTime endTime;

    private List<DayOfWeek> allowedDays;

    private List<LocalDate> excludedDates;

    private List<LockPeriod> lockPeriods;

    private Map<String, String> metadata;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class LockPeriod {
        private String id;
        private String name;
        private String reason;
        private LocalDateTime startTime;
        private LocalDateTime endTime;
        private String createdBy;
    }
}