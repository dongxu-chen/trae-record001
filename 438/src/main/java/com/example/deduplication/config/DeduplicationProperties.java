package com.example.deduplication.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.List;

@Data
@ConfigurationProperties(prefix = "deduplication")
public class DeduplicationProperties {

    private boolean enabled = true;

    private long windowSeconds = 10;

    private long cacheExpireSeconds = 300;

    private String userIdHeader = "X-User-Id";

    private boolean includeQueryParams = true;

    private boolean includeBody = true;

    private List<String> includeHeaders;

    private BloomFilterConfig bloomFilter = new BloomFilterConfig();

    private CaffeineConfig caffeine = new CaffeineConfig();

    private QuorumConfig quorum = new QuorumConfig();

    private DynamicWindowConfig dynamicWindow = new DynamicWindowConfig();

    private FingerprintLearningConfig fingerprintLearning = new FingerprintLearningConfig();

    private AuditConfig audit = new AuditConfig();

    private BypassValidationConfig bypassValidation = new BypassValidationConfig();

    @Data
    public static class BloomFilterConfig {
        private long expectedInsertions = 1000000;
        private double fpp = 0.01;
        private boolean redisConfirmationEnabled = true;
        private long confirmationTtlSeconds = 3600;
    }

    @Data
    public static class CaffeineConfig {
        private long maximumSize = 10000;
        private long expireAfterWriteSeconds = 60;
    }

    @Data
    public static class QuorumConfig {
        private boolean enabled = true;
        private int totalNodes = 3;
        private int writeQuorum = 2;
        private long operationTimeoutMs = 500;
    }

    @Data
    public static class DynamicWindowConfig {
        private boolean enabled = true;
        private long minWindowSeconds = 5;
        private long maxWindowSeconds = 30;
        private long defaultWindowSeconds = 10;
        private long qpsThresholdHigh = 1000;
        private long qpsThresholdLow = 100;
        private int adjustmentFactor = 2;
        private long statisticsWindowSeconds = 60;
    }

    @Data
    public static class FingerprintLearningConfig {
        private boolean enabled = true;
        private long learningWindowSeconds = 3600;
        private int minOccurrencesForPattern = 5;
        private double similarityThreshold = 0.95;
        private int maxPatterns = 10000;
        private long patternExpireHours = 24;
        private boolean autoOptimizeHash = true;
    }

    @Data
    public static class AuditConfig {
        private boolean enabled = true;
        private boolean logToConsole = true;
        private boolean persistToRedis = true;
        private long auditLogTtlSeconds = 86400;
        private int maxAuditRecords = 100000;
        private boolean includeRequestDetails = true;
        private boolean includeResponseDetails = false;
    }

    @Data
    public static class BypassValidationConfig {
        private boolean enabled = true;
        private double sampleRate = 0.01;
        private long minIntervalMs = 1000;
        private boolean compareResponses = true;
        private boolean logMismatches = true;
        private long validationWindowSeconds = 300;
        private int maxParallelValidations = 10;
    }
}
