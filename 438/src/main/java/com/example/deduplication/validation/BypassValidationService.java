package com.example.deduplication.validation;

import com.example.deduplication.config.DeduplicationProperties;
import com.example.deduplication.model.CachedResponse;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
@RequiredArgsConstructor
public class BypassValidationService {

    private static final String VALIDATION_KEY_PREFIX = "deduplication:validation:";
    private static final String BYPASS_MARKER_PREFIX = "deduplication:bypass:";

    private final DeduplicationProperties properties;
    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private final AtomicLong lastValidationTime = new AtomicLong(0);
    private final AtomicInteger parallelValidations = new AtomicInteger(0);
    private final AtomicLong totalValidations = new AtomicLong(0);
    private final AtomicLong mismatchCount = new AtomicLong(0);
    private final Map<String, ValidationResult> validationResults = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        log.info("Bypass Validation Service initialized - sample rate: {}%",
                properties.getBypassValidation().getSampleRate() * 100);
    }

    public Mono<Boolean> shouldBypassValidation(String requestHash) {
        if (!properties.getBypassValidation().isEnabled()) {
            return Mono.just(false);
        }

        long now = System.currentTimeMillis();
        long minInterval = properties.getBypassValidation().getMinIntervalMs();

        if (now - lastValidationTime.get() < minInterval) {
            return Mono.just(false);
        }

        if (parallelValidations.get() >= properties.getBypassValidation().getMaxParallelValidations()) {
            return Mono.just(false);
        }

        String bypassMarkerKey = BYPASS_MARKER_PREFIX + requestHash;
        return redisTemplate.hasKey(bypassMarkerKey)
                .flatMap(hasMarker -> {
                    if (hasMarker) {
                        return Mono.just(false);
                    }

                    double random = Math.random();
                    boolean shouldBypass = random < properties.getBypassValidation().getSampleRate();

                    if (shouldBypass) {
                        lastValidationTime.set(now);
                        parallelValidations.incrementAndGet();
                        return setBypassMarker(bypassMarkerKey)
                                .thenReturn(true);
                    }

                    return Mono.just(false);
                });
    }

    private Mono<Boolean> setBypassMarker(String key) {
        return redisTemplate.opsForValue()
                .set(key, "1", Duration.ofSeconds(properties.getBypassValidation().getValidationWindowSeconds()));
    }

    public Mono<ValidationResult> validateResponse(String requestHash, CachedResponse cachedResponse,
                                                    CachedResponse actualResponse) {
        if (!properties.getBypassValidation().isEnabled()) {
            return Mono.empty();
        }

        totalValidations.incrementAndGet();
        parallelValidations.decrementAndGet();

        boolean match = compareResponses(cachedResponse, actualResponse);
        if (!match) {
            mismatchCount.incrementAndGet();
        }

        ValidationResult result = buildValidationResult(requestHash, cachedResponse, actualResponse, match);

        if (properties.getBypassValidation().isLogMismatches() && !match) {
            logMismatch(result);
        }

        validationResults.put(requestHash, result);

        return saveValidationResult(result)
                .thenReturn(result);
    }

    private boolean compareResponses(CachedResponse cached, CachedResponse actual) {
        if (!properties.getBypassValidation().isCompareResponses()) {
            return true;
        }

        if (cached == null || actual == null) {
            return false;
        }

        if (cached.getStatus() != actual.getStatus()) {
            return false;
        }

        String cachedBody = cached.getBody() != null ? cached.getBody() : "";
        String actualBody = actual.getBody() != null ? actual.getBody() : "";

        return normalizeJson(cachedBody).equals(normalizeJson(actualBody));
    }

    private String normalizeJson(String json) {
        if (json == null || json.isEmpty()) {
            return "";
        }
        try {
            Object obj = objectMapper.readValue(json, Object.class);
            return objectMapper.writeValueAsString(obj);
        } catch (Exception e) {
            return json.replaceAll("\\s+", "");
        }
    }

    private ValidationResult buildValidationResult(String requestHash, CachedResponse cachedResponse,
                                                   CachedResponse actualResponse, boolean match) {
        double similarity = calculateSimilarity(
                cachedResponse != null ? cachedResponse.getBody() : "",
                actualResponse != null ? actualResponse.getBody() : "");

        return ValidationResult.builder()
                .validationId(UUID.randomUUID().toString())
                .requestHash(requestHash)
                .timestamp(System.currentTimeMillis())
                .shouldBypass(true)
                .responseMatch(match)
                .cachedResponseStatus(cachedResponse != null ? cachedResponse.getStatus() : 0)
                .actualResponseStatus(actualResponse != null ? actualResponse.getStatus() : 0)
                .similarityScore(similarity)
                .build();
    }

    private double calculateSimilarity(String str1, String str2) {
        if (str1 == null && str2 == null) return 1.0;
        if (str1 == null || str2 == null) return 0.0;
        if (str1.equals(str2)) return 1.0;

        int distance = levenshteinDistance(str1, str2);
        int maxLen = Math.max(str1.length(), str2.length());

        return maxLen > 0 ? 1.0 - (double) distance / maxLen : 1.0;
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

    private void logMismatch(ValidationResult result) {
        log.warn("[BYPASS_VALIDATION_MISMATCH] hash={}, cachedStatus={}, actualStatus={}, similarity={:.2f}",
                result.getRequestHash(),
                result.getCachedResponseStatus(),
                result.getActualResponseStatus(),
                result.getSimilarityScore());
    }

    private Mono<Void> saveValidationResult(ValidationResult result) {
        String key = VALIDATION_KEY_PREFIX + result.getValidationId();
        try {
            String json = objectMapper.writeValueAsString(result);
            return redisTemplate.opsForValue()
                    .set(key, json, Duration.ofSeconds(properties.getBypassValidation().getValidationWindowSeconds()))
                    .then();
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize validation result", e);
            return Mono.empty();
        }
    }

    @Scheduled(fixedRate = 60000)
    public void reportValidationStats() {
        if (!properties.getBypassValidation().isEnabled()) {
            return;
        }

        long total = totalValidations.get();
        long mismatches = mismatchCount.get();
        double mismatchRate = total > 0 ? (double) mismatches / total * 100 : 0;

        log.info("[VALIDATION_STATS] total_validations={}, mismatches={}, mismatch_rate={:.2f}%, parallel_validations={}",
                total, mismatches, mismatchRate, parallelValidations.get());
    }

    public ValidationStats getValidationStats() {
        long total = totalValidations.get();
        long mismatches = mismatchCount.get();

        return ValidationStats.builder()
                .totalValidations(total)
                .mismatchCount(mismatches)
                .mismatchRate(total > 0 ? (double) mismatches / total * 100 : 0)
                .currentParallelValidations(parallelValidations.get())
                .sampleRate(properties.getBypassValidation().getSampleRate() * 100)
                .build();
    }

    public void resetStats() {
        totalValidations.set(0);
        mismatchCount.set(0);
        validationResults.clear();
    }

    @lombok.Data
    @lombok.Builder
    public static class ValidationStats {
        private long totalValidations;
        private long mismatchCount;
        private double mismatchRate;
        private int currentParallelValidations;
        private double sampleRate;
    }
}
