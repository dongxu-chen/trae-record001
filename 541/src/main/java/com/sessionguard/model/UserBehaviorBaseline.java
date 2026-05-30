package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserBehaviorBaseline implements Serializable {

    private static final long serialVersionUID = 1L;

    private String userId;

    private IpPattern ipPattern;

    private DevicePattern devicePattern;

    private TimePattern timePattern;

    private BehaviorStats stats;

    private LocalDateTime lastUpdatedAt;

    private LocalDateTime createdAt;

    private int version;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class IpPattern implements Serializable {
        private static final long serialVersionUID = 1L;

        private Set<String> commonIps;
        private Set<String> commonSubnets;
        private Set<String> commonCountries;
        private Set<String> commonRegions;
        private Set<String> commonCities;
        private Set<String> knownIsps;
        private double proxyUsageRate;
        private double vpnUsageRate;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DevicePattern implements Serializable {
        private static final long serialVersionUID = 1L;

        private Set<String> commonFingerprintHashes;
        private Set<String> commonBrowsers;
        private Set<String> commonPlatforms;
        private Set<String> commonOs;
        private Set<String> commonTimezones;
        private Set<String> commonLanguages;
        private String mostCommonScreen;
        private double deviceChangeFrequency;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TimePattern implements Serializable {
        private static final long serialVersionUID = 1L;

        private Set<Integer> activeHours;
        private Set<String> activeDays;
        private int avgSessionDurationMinutes;
        private int avgAccessCountPerSession;
        private int maxDailySessions;
        private double avgSessionIntervalMinutes;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class BehaviorStats implements Serializable {
        private static final long serialVersionUID = 1L;

        private long totalSessions;
        private long totalAccessCount;
        private long learningDays;
        private int ipVariabilityScore;
        private int deviceVariabilityScore;
        private double anomalyRate;
        private boolean baselineStable;
        private List<String> recentLocations;
    }
}
