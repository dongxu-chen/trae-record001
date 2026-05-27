package com.security.replayguard.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Data
@Configuration
@ConfigurationProperties(prefix = "replay-guard")
public class ReplayGuardProperties {

    private SlidingWindow slidingWindow = new SlidingWindow();

    private long nonceExpireSeconds = 300;

    private String deviceFingerprintHeader = "X-Device-Fingerprint";

    private String timestampHeader = "X-Timestamp";

    private String nonceHeader = "X-Nonce";

    private Honeypot honeypot = new Honeypot();

    private ConsistentHash consistentHash = new ConsistentHash();

    @Data
    public static class SlidingWindow {
        private int timeWindowSeconds = 60;
        private int maxRequestsPerWindow = 10;
        private boolean dualBufferEnabled = true;
        private int overlapSeconds = 10;
    }

    @Data
    public static class Honeypot {
        private boolean enabled = true;
        private int slowThresholdMs = 2000;
        private int maxSlowRequests = 5;
        private int blockDurationSeconds = 600;
        private boolean dynamicThresholdEnabled = true;
        private double percentile = 0.95;
        private int historyWindowMinutes = 60;
        private int minThresholdMs = 500;
        private int maxThresholdMs = 10000;
        private int adjustmentIntervalSeconds = 300;
    }

    @Data
    public static class ConsistentHash {
        private int virtualNodeCount = 150;
        private List<String> nodes = List.of("node-1", "node-2", "node-3");
    }
}
