package com.replay.detector.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AttackTrace implements Serializable {

    private static final long serialVersionUID = 1L;

    private String traceId;

    private String sourceIp;

    private DeviceFingerprint deviceFingerprint;

    private AttackPattern attackPattern;

    private int totalReplayCount;

    private long firstSeenAt;

    private long lastSeenAt;

    private List<String> targetPaths;

    private Map<String, Integer> pathHitCount;

    private String riskLevel;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DeviceFingerprint implements Serializable {
        private static final long serialVersionUID = 1L;
        private String userAgent;
        private String userAgentHash;
        private String browserType;
        private String osType;
        private boolean isBot;
        boolean isProxy;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AttackPattern implements Serializable {
        private static final long serialVersionUID = 1L;
        private PatternType patternType;
        private double confidence;
        private String description;
        private int burstCount;
        private long avgIntervalMs;
    }

    public enum PatternType {
        SINGLE_PATH_BURST,
        MULTI_PATH_SCAN,
        SLOW_DRIP,
        PERIODIC_PULSE,
        DISTRIBUTED_COORDINATED,
        UNKNOWN
    }
}
