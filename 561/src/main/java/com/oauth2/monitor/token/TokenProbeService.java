package com.oauth2.monitor.token;

import com.oauth2.monitor.metrics.OAuth2Metrics;
import com.oauth2.monitor.tracing.TraceContext;
import io.micrometer.core.instrument.Timer;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

@Slf4j
@Service
public class TokenProbeService {

    private final TokenValidationService tokenValidationService;
    private final OAuth2Metrics metrics;
    private final JwtDecoder jwtDecoder;
    private final ObjectProvider<TraceContext> traceContextProvider;

    @Value("${oauth2.monitor.token-probe.batch-size:100}")
    private int batchSize;

    @Value("${oauth2.monitor.token-probe.concurrency:4}")
    private int concurrency;

    @Value("${oauth2.monitor.token-probe.age-threshold-minutes:30}")
    private int ageThresholdMinutes;

    @Value("${oauth2.monitor.token-probe.expiry-warning-minutes:10}")
    private int expiryWarningMinutes;

    private final ExecutorService probeExecutor;
    private final Map<String, TokenProbeResult> lastProbeResults = new ConcurrentHashMap<>();
    private final List<TokenProbeResult> probeHistory = Collections.synchronizedList(new ArrayList<>());

    private static final int MAX_PROBE_HISTORY = 10000;

    public TokenProbeService(TokenValidationService tokenValidationService,
                             OAuth2Metrics metrics,
                             JwtDecoder jwtDecoder,
                             ObjectProvider<TraceContext> traceContextProvider) {
        this.tokenValidationService = tokenValidationService;
        this.metrics = metrics;
        this.jwtDecoder = jwtDecoder;
        this.traceContextProvider = traceContextProvider;
        this.probeExecutor = Executors.newFixedThreadPool(
                concurrency,
                new ThreadFactory() {
                    private final AtomicInteger counter = new AtomicInteger(0);
                    @Override
                    public Thread newThread(Runnable r) {
                        Thread t = new Thread(r, "token-probe-" + counter.incrementAndGet());
                        t.setDaemon(true);
                        return t;
                    }
                }
        );
    }

    @Scheduled(fixedDelayString = "${oauth2.monitor.token-probe.interval-ms:30000}")
    public void scheduledTokenProbe() {
        String traceId = getTraceId();
        log.info("Starting scheduled token probe - traceId: {}, batchSize: {}, concurrency: {}",
                traceId, batchSize, concurrency);

        try {
            List<TokenInfo> tokensToProbe = selectTokensForProbing();
            if (tokensToProbe.isEmpty()) {
                log.debug("No tokens to probe - traceId: {}", traceId);
                return;
            }

            log.info("Probing {} tokens - traceId: {}", tokensToProbe.size(), traceId);

            List<CompletableFuture<TokenProbeResult>> futures = tokensToProbe.stream()
                    .map(token -> CompletableFuture.supplyAsync(
                            () -> probeToken(token), probeExecutor))
                    .collect(Collectors.toList());

            CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

            List<TokenProbeResult> results = futures.stream()
                    .map(CompletableFuture::join)
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());

            processProbeResults(results);

        } catch (Exception e) {
            log.error("Token probe failed - traceId: {}, error: {}", traceId, e.getMessage(), e);
        }
    }

    private List<TokenInfo> selectTokensForProbing() {
        Instant ageThreshold = Instant.now().minus(ageThresholdMinutes, java.time.temporal.ChronoUnit.MINUTES);

        return tokenValidationService.getActiveTokens().stream()
                .filter(t -> !t.isRevoked() && !t.isExpired())
                .filter(t -> t.getIssuedAt() != null && t.getIssuedAt().isAfter(ageThreshold))
                .filter(t -> t.getTokenType() != null && t.getTokenType().equalsIgnoreCase("bearer"))
                .limit(batchSize)
                .collect(Collectors.toList());
    }

    public TokenProbeResult probeToken(TokenInfo tokenInfo) {
        long startTime = System.currentTimeMillis();
        String traceId = getTraceId();

        TokenProbeResult.TokenProbeResultBuilder resultBuilder = TokenProbeResult.builder()
                .tokenValue(maskToken(tokenInfo.getTokenValue()))
                .probedAt(Instant.now())
                .active(true)
                .validSignature(false)
                .notExpired(false)
                .notRevoked(false)
                .issuerValid(false)
                .audienceValid(false);

        try {
            Timer.Sample sample = metrics.startTokenValidationTimer();
            try {
                Jwt jwt = jwtDecoder.decode(tokenInfo.getTokenValue());
                resultBuilder.validSignature(true);

                Instant expiry = jwt.getExpiresAt();
                if (expiry != null) {
                    boolean expired = Instant.now().isAfter(expiry);
                    resultBuilder.notExpired(!expired);
                    if (!expired) {
                        long secondsToExpiry = java.time.Duration.between(
                                Instant.now(), expiry).getSeconds();
                        resultBuilder.timeToExpirySeconds(secondsToExpiry);

                        if (secondsToExpiry <= expiryWarningMinutes * 60L) {
                            log.warn("Token expiring soon - tokenValue: {}, secondsToExpiry: {}, traceId: {}",
                                    maskToken(tokenInfo.getTokenValue()), secondsToExpiry, traceId);
                        }
                    } else {
                        handleExpiredToken(tokenInfo);
                    }
                } else {
                    resultBuilder.notExpired(true);
                }

                resultBuilder.notRevoked(!tokenInfo.isRevoked());

                String issuer = jwt.getIssuer() != null ? jwt.getIssuer().toString() : null;
                resultBuilder.issuerValid(issuer != null && !issuer.isEmpty());

                List<String> audience = jwt.getAudience();
                resultBuilder.audienceValid(audience != null && !audience.isEmpty());

                if (tokenInfo.isExpired()) {
                    resultBuilder.notExpired(false);
                    handleExpiredToken(tokenInfo);
                }

            } catch (JwtException e) {
                resultBuilder.errorMessage(e.getMessage());
                resultBuilder.validSignature(false);

                if (e.getMessage() != null && e.getMessage().contains("expired")) {
                    resultBuilder.notExpired(false);
                    handleExpiredToken(tokenInfo);
                }

                log.debug("Token probe JWT validation failed - tokenValue: {}, error: {}, traceId: {}",
                        maskToken(tokenInfo.getTokenValue()), e.getMessage(), traceId);

            } finally {
                metrics.stopTokenValidationTimer(sample);
            }

        } catch (Exception e) {
            resultBuilder.errorMessage(e.getMessage());
            log.error("Token probe unexpected error - tokenValue: {}, error: {}, traceId: {}",
                    maskToken(tokenInfo.getTokenValue()), e.getMessage(), traceId);
        }

        resultBuilder.probeLatencyMs(System.currentTimeMillis() - startTime);
        TokenProbeResult result = resultBuilder.build();

        lastProbeResults.put(tokenInfo.getTokenValue(), result);
        addToHistory(result);

        return result;
    }

    private void processProbeResults(List<TokenProbeResult> results) {
        int validCount = 0;
        int expiredCount = 0;
        int revokedCount = 0;
        int invalidCount = 0;
        int expiringSoonCount = 0;

        for (TokenProbeResult result : results) {
            if (result.isCompletelyValid()) {
                validCount++;
                if (result.getTimeToExpirySeconds() > 0 &&
                        result.getTimeToExpirySeconds() <= expiryWarningMinutes * 60L) {
                    expiringSoonCount++;
                }
            } else {
                if (!result.isNotExpired()) expiredCount++;
                if (!result.isNotRevoked()) revokedCount++;
                if (!result.isValidSignature()) invalidCount++;
            }
        }

        log.info(
                "Token probe complete - total: {}, valid: {}, expired: {}, revoked: {}, invalid: {}, expiringSoon: {}",
                results.size(), validCount, expiredCount, revokedCount, invalidCount, expiringSoonCount
        );

        if (expiredCount > 0) {
            log.warn("Detected {} expired tokens during probe", expiredCount);
        }
        if (invalidCount > 0) {
            log.warn("Detected {} invalid signature tokens during probe", invalidCount);
        }
    }

    private void handleExpiredToken(TokenInfo tokenInfo) {
        if (!tokenInfo.isExpired()) {
            tokenInfo.setExpired(true);
            metrics.recordTokenExpired();
            log.info("Token expired during probe - tokenValue: {}, clientId: {}, userId: {}",
                    maskToken(tokenInfo.getTokenValue()),
                    tokenInfo.getClientId(),
                    tokenInfo.getUserId());
        }
    }

    private void addToHistory(TokenProbeResult result) {
        synchronized (probeHistory) {
            if (probeHistory.size() >= MAX_PROBE_HISTORY) {
                probeHistory.remove(0);
            }
            probeHistory.add(result);
        }
    }

    public TokenProbeResult probeTokenImmediate(String tokenValue) {
        TokenInfo tokenInfo = tokenValidationService.getTokenInfo(tokenValue);
        if (tokenInfo == null) {
            return TokenProbeResult.builder()
                    .tokenValue(maskToken(tokenValue))
                    .active(false)
                    .errorMessage("Token not found")
                    .probedAt(Instant.now())
                    .build();
        }
        return probeToken(tokenInfo);
    }

    public List<TokenProbeResult> getLastProbeResults() {
        return new ArrayList<>(lastProbeResults.values());
    }

    public List<TokenProbeResult> getProbeHistory(int limit) {
        List<TokenProbeResult> result = new ArrayList<>();
        synchronized (probeHistory) {
            int start = Math.max(0, probeHistory.size() - limit);
            result.addAll(probeHistory.subList(start, probeHistory.size()));
        }
        return result;
    }

    public Map<String, Object> getProbeStatistics() {
        Map<String, Object> stats = new HashMap<>();
        List<TokenProbeResult> recent = getLastProbeResults();

        long validCount = recent.stream().filter(TokenProbeResult::isCompletelyValid).count();
        long expiredCount = recent.stream().filter(r -> !r.isNotExpired()).count();
        long revokedCount = recent.stream().filter(r -> !r.isNotRevoked()).count();
        long invalidSigCount = recent.stream().filter(r -> !r.isValidSignature()).count();

        double avgLatency = recent.stream()
                .mapToLong(TokenProbeResult::getProbeLatencyMs)
                .average()
                .orElse(0);

        stats.put("totalProbed", recent.size());
        stats.put("validCount", validCount);
        stats.put("expiredCount", expiredCount);
        stats.put("revokedCount", revokedCount);
        stats.put("invalidSignatureCount", invalidSigCount);
        stats.put("averageLatencyMs", String.format("%.2f", avgLatency));
        stats.put("validityRate", recent.isEmpty() ? 0 :
                String.format("%.2f%%", (validCount * 100.0 / recent.size())));

        return stats;
    }

    private String maskToken(String token) {
        if (token == null || token.length() < 8) {
            return "***";
        }
        return token.substring(0, 4) + "..." + token.substring(token.length() - 4);
    }

    private String getTraceId() {
        try {
            TraceContext context = traceContextProvider.getIfAvailable();
            return context != null ? context.getTraceId() : "probe-" + System.currentTimeMillis();
        } catch (Exception e) {
            return "probe-" + System.currentTimeMillis();
        }
    }

    public void shutdown() {
        probeExecutor.shutdown();
        try {
            if (!probeExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                probeExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            probeExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }
}
