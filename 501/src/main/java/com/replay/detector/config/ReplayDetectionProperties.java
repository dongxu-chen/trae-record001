package com.replay.detector.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.Map;

@Data
@Component
@ConfigurationProperties(prefix = "replay.detection")
public class ReplayDetectionProperties {

    private boolean enabled = true;

    private int windowSizeSeconds = 60;

    private int maxReplayCount = 5;

    private BloomFilter bloomFilter = new BloomFilter();

    private Window window = new Window();

    private Webhook webhook = new Webhook();

    private Distributed distributed = new Distributed();

    private Fingerprint fingerprint = new Fingerprint();

    private Adaptive adaptive = new Adaptive();

    private Tracing tracing = new Tracing();

    private Trend trend = new Trend();

    @Data
    public static class BloomFilter {
        private long expectedInsertions = 1000000;
        private double falseProbability = 0.01;
        private boolean confirmationEnabled = true;
    }

    @Data
    public static class Window {
        private boolean dualBufferEnabled = true;
        private int overlapPercent = 50;
    }

    @Data
    public static class Webhook {
        private boolean enabled = true;
        private String url = "http://localhost:9000/alert";
        private String secret;
        private int connectTimeout = 3000;
        private int readTimeout = 5000;
        private Template template = new Template();

        @Data
        public static class Template {
            private String format = "JSON";
            private String bodyTemplate;
            private String jsonTemplate;
            private String xmlTemplate;
            private String textTemplate;
            private Map<String, String> headerTemplates;
        }
    }

    @Data
    public static class Distributed {
        private int lockTimeoutSeconds = 5;
        private String keyPrefix = "replay:lock:";
    }

    @Data
    public static class Fingerprint {
        private boolean includePath = true;
        private boolean includeParams = true;
        private boolean includeUserAgent = true;
        private boolean includeTimestamp = true;
        private int timestampToleranceSeconds = 300;
    }

    @Data
    public static class Adaptive {
        private boolean enabled = true;
        private double baselineQps = 100.0;
        private double highLoadRatio = 2.0;
        private double highLoadSensitivity = 1.5;
        private double lowLoadSensitivity = 0.7;
        private int minReplayCount = 2;
        private int maxReplayCount = 20;
        private int qpsWindowSeconds = 60;
        private long refreshIntervalMs = 30000;
    }

    @Data
    public static class Tracing {
        private boolean enabled = true;
        private int topAttackersLimit = 10;
        private long traceTtlSeconds = 86400;
    }

    @Data
    public static class Trend {
        private boolean enabled = true;
        private int retentionDays = 7;
        private int peakHoursTopN = 5;
    }
}
