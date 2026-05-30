package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MultiPeakTrafficPattern {
    private String serviceId;
    private List<PeriodicPeak> periodicPeaks;
    private List<BurstEvent> burstEvents;
    private double baselineQps;
    private double variance;
    private TrafficType trafficType;

    public enum TrafficType {
        DIURNAL,
        WEEKLY,
        EVENT_DRIVEN,
        SPIKY,
        SUSTAINED
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PeriodicPeak {
        private String name;
        private int startHour;
        private int endHour;
        private double intensity;
        private double width;
        private List<Integer> daysOfWeek;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class BurstEvent {
        private String id;
        private LocalDateTime startTime;
        private int durationMinutes;
        private double intensity;
        private BurstType type;
        private String description;
    }

    public enum BurstType {
        FLASH_SALE,
        MARKETING_PUSH,
        SYSTEM_RECOVERY,
        BATCH_PROCESSING,
        RANDOM_SPIKE
    }
}
