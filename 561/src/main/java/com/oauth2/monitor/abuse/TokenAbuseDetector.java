package com.oauth2.monitor.abuse;

import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.alert.SecurityEvent;
import com.oauth2.monitor.risk.ClientRiskService;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;
import java.util.stream.Collectors;

@Slf4j
@Service
public class TokenAbuseDetector {

    private final AlertService alertService;
    private final ClientRiskService clientRiskService;
    private final MeterRegistry meterRegistry;

    @Value("${oauth2.monitor.abuse.per-token-rate-limit:100}")
    private int perTokenRateLimit;

    @Value("${oauth2.monitor.abuse.per-token-rate-window-seconds:60}")
    private int rateWindowSeconds;

    @Value("${oauth2.monitor.abuse.sudden-spike-threshold:5.0}")
    private double suddenSpikeThreshold;

    @Value("${oauth2.monitor.abuse.concurrent-usage-threshold:3}")
    private int concurrentUsageThreshold;

    @Value("${oauth2.monitor.abuse.unusual-time-window-enabled:true}")
    private boolean unusualTimeWindowEnabled;

    @Value("${oauth2.monitor.abuse.unusual-hour-start:0}")
    private int unusualHourStart;

    @Value("${oauth2.monitor.abuse.unusual-hour-end:6}")
    private int unusualHourEnd;

    @Value("${oauth2.monitor.abuse.auto-block-enabled:true}")
    private boolean autoBlockEnabled;

    @Value("${oauth2.monitor.abuse.block-duration-minutes:15}")
    private int blockDurationMinutes;

    private final Map<String, TokenUsageStats> tokenUsageStats = new ConcurrentHashMap<>();
    private final Set<String> blockedTokens = ConcurrentHashMap.newKeySet();
    private final Map<String, Instant> tokenBlockedUntil = new ConcurrentHashMap<>();

    private final Map<String, LongAdder> requestCounters = new ConcurrentHashMap<>();
    private final Map<String, Queue<Long>> rateHistory = new ConcurrentHashMap<>();

    private static final int MAX_TOKENS_TRACKED = 10000;
    private static final int RATE_HISTORY_SIZE = 60;

    public TokenAbuseDetector(AlertService alertService, ClientRiskService clientRiskService,
                               MeterRegistry meterRegistry) {
        this.alertService = alertService;
        this.clientRiskService = clientRiskService;
        this.meterRegistry = meterRegistry;

        Gauge.builder("oauth2_abuse_tracked_tokens", tokenUsageStats::size)
                .description("Number of tokens being tracked for abuse")
                .register(meterRegistry);

        Gauge.builder("oauth2_abuse_blocked_tokens", blockedTokens::size)
                .description("Number of currently blocked tokens")
                .register(meterRegistry);
    }

    public void recordTokenUsage(String tokenValue, String clientId, String userId, String ipAddress) {
        String maskedToken = maskToken(tokenValue);

        if (isTokenBlocked(tokenValue)) {
            log.debug("Request from blocked token: {}", maskedToken);
            requestCounters.computeIfAbsent(tokenValue, k -> new LongAdder()).increment();
            return;
        }

        TokenUsageStats stats = tokenUsageStats.computeIfAbsent(tokenValue, k ->
                new TokenUsageStats(tokenValue, clientId, userId));

        stats.recordUsage(ipAddress);
        requestCounters.computeIfAbsent(tokenValue, k -> new LongAdder()).increment();

        checkRateAbuse(tokenValue, stats, clientId, userId, ipAddress);
        checkConcurrentUsage(tokenValue, stats, clientId, userId);
        checkUnusualTimeUsage(tokenValue, stats, clientId, userId, ipAddress);
        checkSuddenSpike(tokenValue, stats, clientId, userId);

        cleanupOldTokens();
    }

    private void checkRateAbuse(String tokenValue, TokenUsageStats stats, String clientId,
                                  String userId, String ipAddress) {
        double currentRate = stats.getRequestsPerSecond(rateWindowSeconds);

        if (currentRate > perTokenRateLimit) {
            log.warn("Rate limit exceeded for token {}: {} req/s (limit: {})",
                    maskToken(tokenValue), String.format("%.1f", currentRate), perTokenRateLimit);

            stats.incrementRateViolations();

            if (stats.getRateViolations() >= 3 && autoBlockEnabled) {
                blockToken(tokenValue, clientId, userId, "Rate limit exceeded: " +
                        String.format("%.1f", currentRate) + " req/s");
            }

            alertService.recordSecurityEvent(
                    SecurityEvent.EventType.RATE_LIMIT_EXCEEDED,
                    "Token rate limit exceeded: " + String.format("%.1f", currentRate) + " req/s",
                    Map.of(
                            "tokenValue", maskToken(tokenValue),
                            "clientId", clientId,
                            "userId", userId,
                            "ipAddress", ipAddress,
                            "currentRate", String.format("%.1f", currentRate),
                            "limit", String.valueOf(perTokenRateLimit),
                            "violationCount", String.valueOf(stats.getRateViolations())
                    )
            );

            clientRiskService.recordRateLimitViolation(clientId);
        }
    }

    private void checkConcurrentUsage(String tokenValue, TokenUsageStats stats,
                                        String clientId, String userId) {
        Set<String> uniqueIps = stats.getUniqueIps(rateWindowSeconds);

        if (uniqueIps.size() >= concurrentUsageThreshold) {
            log.warn("Concurrent usage detected for token {}: {} distinct IPs",
                    maskToken(tokenValue), uniqueIps.size());

            stats.incrementConcurrentViolations();

            alertService.recordSecurityEvent(
                    SecurityEvent.EventType.CONCURRENT_SESSIONS,
                    "Token used from " + uniqueIps.size() + " distinct IPs concurrently",
                    Map.of(
                            "tokenValue", maskToken(tokenValue),
                            "clientId", clientId,
                            "userId", userId,
                            "distinctIps", String.valueOf(uniqueIps.size()),
                            "threshold", String.valueOf(concurrentUsageThreshold),
                            "violationCount", String.valueOf(stats.getConcurrentViolations())
                    )
            );

            clientRiskService.recordAbuseScore(clientId, 5.0);
        }
    }

    private void checkUnusualTimeUsage(String tokenValue, TokenUsageStats stats,
                                         String clientId, String userId, String ipAddress) {
        if (!unusualTimeWindowEnabled) return;

        int currentHour = Instant.now().atZone(java.time.ZoneId.systemDefault()).getHour();
        boolean isUnusualTime = currentHour >= unusualHourStart && currentHour < unusualHourEnd;

        if (isUnusualTime) {
            stats.incrementUnusualTimeUsage();

            if (stats.getUnusualTimeUsage() >= 5) {
                alertService.recordSecurityEvent(
                        SecurityEvent.EventType.UNUSUAL_LOCATION,
                        "Suspicious activity during unusual hours",
                        Map.of(
                                "tokenValue", maskToken(tokenValue),
                                "clientId", clientId,
                                "userId", userId,
                                "ipAddress", ipAddress,
                                "currentHour", String.valueOf(currentHour),
                                "unusualWindow", unusualHourStart + "-" + unusualHourEnd,
                                "unusualUsageCount", String.valueOf(stats.getUnusualTimeUsage())
                        )
                );

                clientRiskService.recordAbuseScore(clientId, 3.0);
            }
        }
    }

    private void checkSuddenSpike(String tokenValue, TokenUsageStats stats,
                                    String clientId, String userId) {
        Queue<Long> history = rateHistory.computeIfAbsent(tokenValue, k -> new LinkedList<>());

        long currentRequests = requestCounters.getOrDefault(tokenValue, new LongAdder()).sum();
        history.offer(currentRequests);

        while (history.size() > RATE_HISTORY_SIZE) {
            history.poll();
        }

        if (history.size() >= 10) {
            List<Long> rates = new ArrayList<>(history);
            double avg = rates.subList(0, rates.size() - 1).stream()
                    .mapToLong(Long::longValue)
                    .average()
                    .orElse(1.0);

            double spikeRatio = currentRequests / Math.max(1.0, avg);

            if (spikeRatio >= suddenSpikeThreshold) {
                log.warn("Sudden traffic spike for token {}: {}x increase",
                        maskToken(tokenValue), String.format("%.1f", spikeRatio));

                stats.incrementSpikeViolations();

                alertService.recordSecurityEvent(
                        SecurityEvent.EventType.SUSPICIOUS_ACTIVITY,
                        "Sudden traffic spike: " + String.format("%.1f", spikeRatio) + "x increase",
                        Map.of(
                                "tokenValue", maskToken(tokenValue),
                                "clientId", clientId,
                                "userId", userId,
                                "spikeRatio", String.format("%.1f", spikeRatio),
                                "threshold", String.valueOf(suddenSpikeThreshold),
                                "spikeViolationCount", String.valueOf(stats.getSpikeViolations())
                        )
                );

                clientRiskService.recordAbuseScore(clientId, 4.0);
            }
        }
    }

    public void blockToken(String tokenValue, String clientId, String userId, String reason) {
        blockedTokens.add(tokenValue);
        tokenBlockedUntil.put(tokenValue, Instant.now().plus(Duration.ofMinutes(blockDurationMinutes)));

        log.warn("Token blocked for {} minutes: {} - reason: {}",
                blockDurationMinutes, maskToken(tokenValue), reason);

        alertService.recordSecurityEvent(
                SecurityEvent.EventType.SUSPICIOUS_ACTIVITY,
                "Token blocked: " + reason,
                Map.of(
                        "tokenValue", maskToken(tokenValue),
                        "clientId", clientId,
                        "userId", userId,
                        "reason", reason,
                        "blockDurationMinutes", String.valueOf(blockDurationMinutes)
                )
        );
    }

    public boolean isTokenBlocked(String tokenValue) {
        if (!blockedTokens.contains(tokenValue)) {
            return false;
        }

        Instant blockedUntil = tokenBlockedUntil.get(tokenValue);
        if (blockedUntil != null && Instant.now().isAfter(blockedUntil)) {
            unblockToken(tokenValue);
            return false;
        }

        return true;
    }

    public void unblockToken(String tokenValue) {
        blockedTokens.remove(tokenValue);
        tokenBlockedUntil.remove(tokenValue);
        log.info("Token unblocked: {}", maskToken(tokenValue));
    }

    @Scheduled(fixedDelay = 60000)
    public void cleanupExpiredBlocks() {
        int unblockedCount = 0;
        Iterator<Map.Entry<String, Instant>> iterator = tokenBlockedUntil.entrySet().iterator();

        while (iterator.hasNext()) {
            Map.Entry<String, Instant> entry = iterator.next();
            if (Instant.now().isAfter(entry.getValue())) {
                blockedTokens.remove(entry.getKey());
                iterator.remove();
                unblockedCount++;
            }
        }

        if (unblockedCount > 0) {
            log.info("Cleaned up {} expired token blocks", unblockedCount);
        }
    }

    private void cleanupOldTokens() {
        if (tokenUsageStats.size() > MAX_TOKENS_TRACKED) {
            tokenUsageStats.entrySet().stream()
                    .sorted(Map.Entry.comparingByValue(
                            Comparator.comparingLong(TokenUsageStats::getLastUsedTimestamp)))
                    .limit(tokenUsageStats.size() - MAX_TOKENS_TRACKED)
                    .forEach(entry -> {
                        tokenUsageStats.remove(entry.getKey());
                        requestCounters.remove(entry.getKey());
                        rateHistory.remove(entry.getKey());
                    });
        }
    }

    public List<TokenUsageStats> getHighUsageTokens(int limit) {
        return tokenUsageStats.values().stream()
                .sorted(Comparator.comparingDouble(
                        (TokenUsageStats s) -> s.getRequestsPerSecond(rateWindowSeconds)).reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<Map<String, Object>> getAbuseAlerts(int limit) {
        return tokenUsageStats.values().stream()
                .filter(s -> s.getRateViolations() > 0 ||
                        s.getConcurrentViolations() > 0 ||
                        s.getSpikeViolations() > 0)
                .sorted(Comparator.comparingInt(
                                (TokenUsageStats s) -> s.getRateViolations() +
                                        s.getConcurrentViolations() + s.getSpikeViolations())
                        .reversed())
                .limit(limit)
                .map(s -> Map.of(
                        "tokenValue", maskToken(s.getTokenValue()),
                        "clientId", s.getClientId(),
                        "userId", s.getUserId(),
                        "rateViolations", String.valueOf(s.getRateViolations()),
                        "concurrentViolations", String.valueOf(s.getConcurrentViolations()),
                        "spikeViolations", String.valueOf(s.getSpikeViolations()),
                        "currentRate", String.format("%.1f", s.getRequestsPerSecond(rateWindowSeconds))
                ))
                .collect(Collectors.toList());
    }

    public Set<String> getBlockedTokens() {
        return blockedTokens.stream()
                .map(this::maskToken)
                .collect(Collectors.toSet());
    }

    public TokenUsageStats getTokenStats(String tokenValue) {
        return tokenUsageStats.get(tokenValue);
    }

    public int getTrackedTokenCount() {
        return tokenUsageStats.size();
    }

    public int getBlockedTokenCount() {
        return blockedTokens.size();
    }

    private String maskToken(String token) {
        if (token == null || token.length() < 8) {
            return "***";
        }
        return token.substring(0, 4) + "..." + token.substring(token.length() - 4);
    }

    public static class TokenUsageStats {
        private final String tokenValue;
        private final String clientId;
        private final String userId;
        private final Queue<UsageRecord> usageHistory = new LinkedList<>();
        private final AtomicInteger rateViolations = new AtomicInteger(0);
        private final AtomicInteger concurrentViolations = new AtomicInteger(0);
        private final AtomicInteger spikeViolations = new AtomicInteger(0);
        private final AtomicInteger unusualTimeUsage = new AtomicInteger(0);
        private final AtomicLong lastUsedTimestamp = new AtomicLong(0);
        private final Set<String> recentIps = ConcurrentHashMap.newKeySet();

        public TokenUsageStats(String tokenValue, String clientId, String userId) {
            this.tokenValue = tokenValue;
            this.clientId = clientId;
            this.userId = userId;
        }

        public synchronized void recordUsage(String ipAddress) {
            usageHistory.offer(new UsageRecord(Instant.now().toEpochMilli(), ipAddress));
            lastUsedTimestamp.set(Instant.now().toEpochMilli());
            recentIps.add(ipAddress);

            while (usageHistory.size() > 10000) {
                usageHistory.poll();
            }

            if (recentIps.size() > 50) {
                recentIps.clear();
            }
        }

        public synchronized double getRequestsPerSecond(int windowSeconds) {
            long cutoff = Instant.now().minus(Duration.ofSeconds(windowSeconds)).toEpochMilli();
            long count = usageHistory.stream()
                    .filter(r -> r.timestamp() >= cutoff)
                    .count();
            return (double) count / windowSeconds;
        }

        public synchronized Set<String> getUniqueIps(int windowSeconds) {
            long cutoff = Instant.now().minus(Duration.ofSeconds(windowSeconds)).toEpochMilli();
            return usageHistory.stream()
                    .filter(r -> r.timestamp() >= cutoff)
                    .map(UsageRecord::ipAddress)
                    .collect(Collectors.toSet());
        }

        public String getTokenValue() { return tokenValue; }
        public String getClientId() { return clientId; }
        public String getUserId() { return userId; }
        public int getRateViolations() { return rateViolations.get(); }
        public int getConcurrentViolations() { return concurrentViolations.get(); }
        public int getSpikeViolations() { return spikeViolations.get(); }
        public int getUnusualTimeUsage() { return unusualTimeUsage.get(); }
        public long getLastUsedTimestamp() { return lastUsedTimestamp.get(); }

        public void incrementRateViolations() { rateViolations.incrementAndGet(); }
        public void incrementConcurrentViolations() { concurrentViolations.incrementAndGet(); }
        public void incrementSpikeViolations() { spikeViolations.incrementAndGet(); }
        public void incrementUnusualTimeUsage() { unusualTimeUsage.incrementAndGet(); }
    }

    public record UsageRecord(long timestamp, String ipAddress) {}
}
