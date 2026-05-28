package com.example.deduplication.learning;

import com.example.deduplication.config.DeduplicationProperties;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.hash.Hashing;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
@RequiredArgsConstructor
public class FingerprintLearningService {

    private static final String PATTERN_KEY_PREFIX = "deduplication:pattern:";
    private static final String FINGERPRINT_KEY_PREFIX = "deduplication:fingerprint:";

    private final DeduplicationProperties properties;
    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private final Map<String, RequestPattern> localPatterns = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> fingerprintCounts = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        log.info("Fingerprint Learning Service initialized");
    }

    public String generateFingerprint(ServerHttpRequest request, String body, String userId) {
        StringBuilder sb = new StringBuilder();
        sb.append(request.getMethod()).append(":");
        sb.append(request.getPath().value()).append(":");
        sb.append(userId).append(":");

        if (properties.getFingerprintLearning().isAutoOptimizeHash()) {
            String simplifiedBody = simplifyBody(body);
            sb.append(simplifiedBody);
        } else {
            sb.append(body);
        }

        return Hashing.murmur3_128()
                .hashString(sb.toString(), StandardCharsets.UTF_8)
                .toString();
    }

    private String simplifyBody(String body) {
        if (body == null || body.isEmpty()) {
            return "";
        }

        String simplified = body.replaceAll("\"[^\"]*\"", "\"v\"")
                .replaceAll("\\d+", "N")
                .replaceAll("\\s+", "");

        return simplified;
    }

    public Mono<Boolean> isKnownPattern(String fingerprint) {
        if (!properties.getFingerprintLearning().isEnabled()) {
            return Mono.just(false);
        }

        AtomicLong count = fingerprintCounts.get(fingerprint);
        if (count != null && count.get() >= properties.getFingerprintLearning().getMinOccurrencesForPattern()) {
            return Mono.just(true);
        }

        String countKey = FINGERPRINT_KEY_PREFIX + fingerprint + ":count";
        return redisTemplate.opsForValue().get(countKey)
                .map(c -> Long.parseLong(c) >= properties.getFingerprintLearning().getMinOccurrencesForPattern())
                .defaultIfEmpty(false);
    }

    public Mono<Void> recordFingerprint(String fingerprint, ServerHttpRequest request, String userId) {
        if (!properties.getFingerprintLearning().isEnabled()) {
            return Mono.empty();
        }

        fingerprintCounts.computeIfAbsent(fingerprint, k -> new AtomicLong(0))
                .incrementAndGet();

        String countKey = FINGERPRINT_KEY_PREFIX + fingerprint + ":count";
        String patternKey = PATTERN_KEY_PREFIX + fingerprint;

        return redisTemplate.opsForValue().increment(countKey)
                .flatMap(count -> {
                    if (count >= properties.getFingerprintLearning().getMinOccurrencesForPattern()) {
                        RequestPattern pattern = buildPattern(fingerprint, request, userId, count);
                        localPatterns.put(fingerprint, pattern);
                        return savePatternToRedis(patternKey, pattern);
                    }
                    return Mono.empty();
                })
                .then();
    }

    private RequestPattern buildPattern(String fingerprint, ServerHttpRequest request,
                                        String userId, long count) {
        return RequestPattern.builder()
                .patternId(fingerprint)
                .pathPattern(request.getPath().value())
                .method(request.getMethod().name())
                .userIdPattern(userId)
                .occurrenceCount(new AtomicLong(count))
                .firstSeenTimestamp(System.currentTimeMillis())
                .lastSeenTimestamp(System.currentTimeMillis())
                .similarityScore(1.0)
                .isVerifiedPattern(true)
                .deduplicationCount(0)
                .build();
    }

    private Mono<Void> savePatternToRedis(String key, RequestPattern pattern) {
        try {
            String json = objectMapper.writeValueAsString(pattern);
            return redisTemplate.opsForValue()
                    .set(key, json, Duration.ofHours(properties.getFingerprintLearning().getPatternExpireHours()))
                    .then();
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize pattern", e);
            return Mono.empty();
        }
    }

    public double calculateSimilarity(String fingerprint1, String fingerprint2) {
        if (fingerprint1.equals(fingerprint2)) {
            return 1.0;
        }

        int distance = levenshteinDistance(fingerprint1, fingerprint2);
        int maxLen = Math.max(fingerprint1.length(), fingerprint2.length());

        return 1.0 - (double) distance / maxLen;
    }

    private int levenshteinDistance(String s1, String s2) {
        int[][] dp = new int[s1.length() + 1][s2.length() + 1];

        for (int i = 0; i <= s1.length(); i++) {
            dp[i][0] = i;
        }
        for (int j = 0; j <= s2.length(); j++) {
            dp[0][j] = j;
        }

        for (int i = 1; i <= s1.length(); i++) {
            for (int j = 1; j <= s2.length(); j++) {
                int cost = s1.charAt(i - 1) == s2.charAt(j - 1) ? 0 : 1;
                dp[i][j] = Math.min(Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1),
                        dp[i - 1][j - 1] + cost);
            }
        }

        return dp[s1.length()][s2.length()];
    }

    @Scheduled(fixedRate = 60000)
    public void cleanupOldPatterns() {
        if (!properties.getFingerprintLearning().isEnabled()) {
            return;
        }

        long cutoffTime = System.currentTimeMillis() -
                (properties.getFingerprintLearning().getLearningWindowSeconds() * 1000);

        fingerprintCounts.entrySet().removeIf(entry -> {
            RequestPattern pattern = localPatterns.get(entry.getKey());
            return pattern != null && pattern.getLastSeenTimestamp() < cutoffTime;
        });

        if (localPatterns.size() > properties.getFingerprintLearning().getMaxPatterns()) {
            localPatterns.clear();
            fingerprintCounts.clear();
            log.info("Cleared local pattern cache due to size limit");
        }

        log.debug("Fingerprint learning stats - patterns: {}, fingerprints: {}",
                localPatterns.size(), fingerprintCounts.size());
    }

    public PatternStats getPatternStats() {
        return PatternStats.builder()
                .totalPatterns(localPatterns.size())
                .totalFingerprints(fingerprintCounts.size())
                .verifiedPatterns((int) localPatterns.values().stream()
                        .filter(RequestPattern::isVerifiedPattern)
                        .count())
                .build();
    }

    @lombok.Data
    @lombok.Builder
    public static class PatternStats {
        private int totalPatterns;
        private int totalFingerprints;
        private int verifiedPatterns;
    }
}
