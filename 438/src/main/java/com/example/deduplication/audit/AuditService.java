package com.example.deduplication.audit;

import com.example.deduplication.config.DeduplicationProperties;
import com.example.deduplication.model.CachedResponse;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuditService {

    private static final String AUDIT_LOG_KEY_PREFIX = "deduplication:audit:";
    private static final String AUDIT_STATS_KEY = "deduplication:audit:stats";

    private final DeduplicationProperties properties;
    private final ReactiveStringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private final ConcurrentLinkedQueue<DeduplicationAuditLog> auditLogBuffer = new ConcurrentLinkedQueue<>();
    private final AtomicLong totalDuplicates = new AtomicLong(0);
    private final AtomicLong totalRequests = new AtomicLong(0);
    private final Map<String, AtomicLong> duplicateByUserId = new HashMap<>();
    private final Map<String, AtomicLong> duplicateByPath = new HashMap<>();
    private final Map<String, AtomicLong> duplicateBySource = new HashMap<>();

    @PostConstruct
    public void init() {
        log.info("Audit Service initialized");
    }

    public Mono<Void> recordDuplicateRequest(ServerHttpRequest request, String requestHash,
                                              String fingerprint, CachedResponse cachedResponse,
                                              String source, long startTime) {
        if (!properties.getAudit().isEnabled()) {
            return Mono.empty();
        }

        totalDuplicates.incrementAndGet();

        DeduplicationAuditLog auditLog = buildAuditLog(request, requestHash, fingerprint,
                cachedResponse, source, startTime, true);

        if (properties.getAudit().isLogToConsole()) {
            logAudit(auditLog);
        }

        aggregateStats(auditLog);

        if (properties.getAudit().isPersistToRedis()) {
            auditLogBuffer.offer(auditLog);
        }

        return Mono.empty();
    }

    public Mono<Void> recordFirstRequest(ServerHttpRequest request, String requestHash,
                                         String fingerprint, long startTime) {
        if (!properties.getAudit().isEnabled()) {
            return Mono.empty();
        }

        totalRequests.incrementAndGet();

        DeduplicationAuditLog auditLog = buildAuditLog(request, requestHash, fingerprint,
                null, "first_request", startTime, false);

        aggregateStats(auditLog);

        return Mono.empty();
    }

    private DeduplicationAuditLog buildAuditLog(ServerHttpRequest request, String requestHash,
                                                String fingerprint, CachedResponse cachedResponse,
                                                String source, long startTime, boolean isDuplicate) {
        DeduplicationAuditLog.DeduplicationAuditLogBuilder builder = DeduplicationAuditLog.builder()
                .auditId(UUID.randomUUID().toString())
                .requestHash(requestHash)
                .requestFingerprint(fingerprint)
                .timestamp(System.currentTimeMillis())
                .userId(request.getHeaders().getFirst(properties.getUserIdHeader()))
                .clientIp(getClientIp(request))
                .method(request.getMethod().name())
                .path(request.getPath().value())
                .isDuplicate(isDuplicate)
                .source(source)
                .processingTimeMs(System.currentTimeMillis() - startTime);

        if (properties.getAudit().isIncludeRequestDetails()) {
            Map<String, String> headers = new HashMap<>();
            request.getHeaders().forEach((k, v) -> headers.put(k, String.join(",", v)));
            builder.requestHeaders(headers);
        }

        if (cachedResponse != null) {
            builder.responseStatus(cachedResponse.getStatus());
            if (properties.getAudit().isIncludeResponseDetails()) {
                builder.responseBody(cachedResponse.getBody());
            }
        }

        return builder.build();
    }

    private String getClientIp(ServerHttpRequest request) {
        String xForwardedFor = request.getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        String xRealIp = request.getHeaders().getFirst("X-Real-IP");
        if (xRealIp != null && !xRealIp.isEmpty()) {
            return xRealIp;
        }
        return request.getRemoteAddress() != null ?
                request.getRemoteAddress().getAddress().getHostAddress() : "unknown";
    }

    private void aggregateStats(DeduplicationAuditLog auditLog) {
        if (auditLog.isDuplicate()) {
            duplicateByUserId.computeIfAbsent(auditLog.getUserId(), k -> new AtomicLong(0))
                    .incrementAndGet();
            duplicateByPath.computeIfAbsent(auditLog.getPath(), k -> new AtomicLong(0))
                    .incrementAndGet();
            duplicateBySource.computeIfAbsent(auditLog.getSource(), k -> new AtomicLong(0))
                    .incrementAndGet();
        }
    }

    private void logAudit(DeduplicationAuditLog auditLog) {
        log.info("[DEDUPLICATION_AUDIT] duplicate={}, hash={}, user={}, ip={}, method={}, path={}, source={}, time={}ms",
                auditLog.isDuplicate(),
                auditLog.getRequestHash(),
                auditLog.getUserId(),
                auditLog.getClientIp(),
                auditLog.getMethod(),
                auditLog.getPath(),
                auditLog.getSource(),
                auditLog.getProcessingTimeMs());
    }

    @Scheduled(fixedRate = 5000)
    public void flushAuditLogs() {
        if (!properties.getAudit().isEnabled() || !properties.getAudit().isPersistToRedis()) {
            return;
        }

        int flushCount = 0;
        while (!auditLogBuffer.isEmpty() && flushCount < properties.getAudit().getMaxAuditRecords()) {
            DeduplicationAuditLog auditLog = auditLogBuffer.poll();
            if (auditLog != null) {
                saveAuditLogToRedis(auditLog).subscribe();
                flushCount++;
            }
        }
    }

    private Mono<Void> saveAuditLogToRedis(DeduplicationAuditLog auditLog) {
        String key = AUDIT_LOG_KEY_PREFIX + auditLog.getAuditId();
        try {
            String json = objectMapper.writeValueAsString(auditLog);
            return redisTemplate.opsForValue()
                    .set(key, json, Duration.ofSeconds(properties.getAudit().getAuditLogTtlSeconds()))
                    .then();
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize audit log", e);
            return Mono.empty();
        }
    }

    @Scheduled(fixedRate = 60000)
    public void reportStats() {
        if (!properties.getAudit().isEnabled()) {
            return;
        }

        long total = totalRequests.get();
        long duplicates = totalDuplicates.get();
        double rate = total > 0 ? (double) duplicates / total * 100 : 0;

        log.info("[AUDIT_STATS] total_requests={}, duplicates={}, duplicate_rate={:.2f}%, top_users={}, top_paths={}, top_sources={}",
                total, duplicates, rate,
                getTopEntries(duplicateByUserId, 5),
                getTopEntries(duplicateByPath, 5),
                getTopEntries(duplicateBySource, 5));
    }

    private Map<String, Long> getTopEntries(Map<String, AtomicLong> map, int limit) {
        return map.entrySet().stream()
                .sorted((a, b) -> Long.compare(b.getValue().get(), a.getValue().get()))
                .limit(limit)
                .collect(HashMap::new, (m, e) -> m.put(e.getKey(), e.getValue().get()), HashMap::putAll);
    }

    public AuditStats getAuditStats() {
        return AuditStats.builder()
                .totalRequests(totalRequests.get())
                .totalDuplicates(totalDuplicates.get())
                .duplicateRate(totalRequests.get() > 0 ?
                        (double) totalDuplicates.get() / totalRequests.get() * 100 : 0)
                .duplicateByUserId(new HashMap<>(duplicateByUserId))
                .duplicateByPath(new HashMap<>(duplicateByPath))
                .duplicateBySource(new HashMap<>(duplicateBySource))
                .build();
    }

    public void resetStats() {
        totalRequests.set(0);
        totalDuplicates.set(0);
        duplicateByUserId.clear();
        duplicateByPath.clear();
        duplicateBySource.clear();
    }

    @lombok.Data
    @lombok.Builder
    public static class AuditStats {
        private long totalRequests;
        private long totalDuplicates;
        private double duplicateRate;
        private Map<String, AtomicLong> duplicateByUserId;
        private Map<String, AtomicLong> duplicateByPath;
        private Map<String, AtomicLong> duplicateBySource;
    }
}
