package com.example.deduplication.core;

import com.example.deduplication.audit.AuditService;
import com.example.deduplication.bloom.BloomFilterService;
import com.example.deduplication.cache.LocalCacheService;
import com.example.deduplication.config.DeduplicationProperties;
import com.example.deduplication.learning.FingerprintLearningService;
import com.example.deduplication.model.CachedResponse;
import com.example.deduplication.model.DeduplicationResult;
import com.example.deduplication.quorum.QuorumService;
import com.example.deduplication.stats.DynamicWindowManager;
import com.example.deduplication.stats.QpsStatisticsService;
import com.example.deduplication.validation.BypassValidationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import reactor.core.publisher.Mono;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeduplicationService {

    private static final long LOCK_EXPIRE_SECONDS = 30;

    private final DeduplicationProperties properties;
    private final RequestHashGenerator hashGenerator;
    private final BloomFilterService bloomFilterService;
    private final LocalCacheService localCacheService;
    private final QuorumService quorumService;
    private final DynamicWindowManager windowManager;
    private final QpsStatisticsService qpsStatisticsService;
    private final FingerprintLearningService fingerprintLearningService;
    private final AuditService auditService;
    private final BypassValidationService bypassValidationService;

    public Mono<DeduplicationResult> checkDuplicate(ServerHttpRequest request, String body) {
        if (!properties.isEnabled()) {
            return Mono.just(DeduplicationResult.firstRequest(null));
        }

        long startTime = System.currentTimeMillis();
        qpsStatisticsService.recordRequest();

        String userId = request.getHeaders().getFirst(properties.getUserIdHeader());
        if (!StringUtils.hasText(userId)) {
            userId = "anonymous";
        }

        String hash = hashGenerator.generateHash(request, body);
        String fingerprint = fingerprintLearningService.generateFingerprint(request, body, userId);
        long currentWindow = windowManager.getCurrentWindowSeconds();

        return bypassValidationService.shouldBypassValidation(hash)
                .flatMap(shouldBypass -> {
                    if (shouldBypass) {
                        log.info("Bypass validation enabled for hash: {}", hash);
                        return Mono.just(DeduplicationResult.builder()
                                .isDuplicate(false)
                                .requestHash(hash)
                                .shouldProcess(true)
                                .isBypassValidation(true)
                                .fingerprint(fingerprint)
                                .build());
                    }

                    return checkWithDeduplication(request, body, hash, fingerprint,
                            currentWindow, startTime, userId);
                });
    }

    private Mono<DeduplicationResult> checkWithDeduplication(ServerHttpRequest request, String body,
                                                              String hash, String fingerprint,
                                                              long currentWindow, long startTime, String userId) {
        return fingerprintLearningService.isKnownPattern(fingerprint)
                .flatMap(isKnownPattern -> {
                    if (isKnownPattern) {
                        log.debug("Known pattern detected: {}", fingerprint);
                    }

                    return bloomFilterService.mightContainWithConfirmation(hash)
                            .flatMap(bloomContains -> {
                                if (!bloomContains) {
                                    log.info("New request detected (bloom filter pass), hash: {}, window: {}s", hash, currentWindow);
                                    return bloomFilterService.putWithConfirmation(hash)
                                            .then(fingerprintLearningService.recordFingerprint(fingerprint, request, userId))
                                            .then(auditService.recordFirstRequest(request, hash, fingerprint, startTime))
                                            .then(Mono.just(DeduplicationResult.builder()
                                                    .isDuplicate(false)
                                                    .requestHash(hash)
                                                    .shouldProcess(true)
                                                    .fingerprint(fingerprint)
                                                    .build()));
                                }

                                CachedResponse localCached = localCacheService.get(hash);
                                if (localCached != null && !localCached.isExpired(currentWindow)) {
                                    log.info("Duplicate request detected in local cache, hash: {}, window: {}s", hash, currentWindow);
                                    return auditService.recordDuplicateRequest(request, hash, fingerprint,
                                                    localCached, "local_cache", startTime)
                                            .then(Mono.just(DeduplicationResult.duplicate(localCached, hash)));
                                }

                                return quorumService.quorumGet(hash)
                                        .switchIfEmpty(Mono.defer(() -> {
                                            log.info("Request not in distributed cache, hash: {}", hash);
                                            return Mono.just(CachedResponse.builder().status(-1).build());
                                        }))
                                        .flatMap(distributedCached -> {
                                            if (distributedCached.getStatus() == -1) {
                                                return quorumService.quorumTryLock(hash, LOCK_EXPIRE_SECONDS)
                                                        .flatMap(locked -> {
                                                            if (locked) {
                                                                log.info("Lock acquired, proceeding with first request, hash: {}", hash);
                                                                return fingerprintLearningService.recordFingerprint(fingerprint, request, userId)
                                                                        .then(auditService.recordFirstRequest(request, hash, fingerprint, startTime))
                                                                        .then(Mono.just(DeduplicationResult.builder()
                                                                                .isDuplicate(false)
                                                                                .requestHash(hash)
                                                                                .shouldProcess(true)
                                                                                .fingerprint(fingerprint)
                                                                                .build()));
                                                            } else {
                                                                return Mono.delay(java.time.Duration.ofMillis(100))
                                                                        .then(quorumService.quorumGet(hash))
                                                                        .flatMap(response -> {
                                                                            if (response != null && !response.isExpired(currentWindow)) {
                                                                                log.info("Duplicate request detected after waiting for lock, hash: {}", hash);
                                                                                localCacheService.put(hash, response);
                                                                                return auditService.recordDuplicateRequest(request, hash, fingerprint,
                                                                                                response, "distributed_cache_lock", startTime)
                                                                                        .then(Mono.just(DeduplicationResult.duplicate(response, hash)));
                                                                            }
                                                                            return fingerprintLearningService.recordFingerprint(fingerprint, request, userId)
                                                                                    .then(auditService.recordFirstRequest(request, hash, fingerprint, startTime))
                                                                                    .then(Mono.just(DeduplicationResult.builder()
                                                                                            .isDuplicate(false)
                                                                                            .requestHash(hash)
                                                                                            .shouldProcess(true)
                                                                                            .fingerprint(fingerprint)
                                                                                            .build()));
                                                                        });
                                                            }
                                                        });
                                            }

                                            if (!distributedCached.isExpired(currentWindow)) {
                                                log.info("Duplicate request detected in distributed cache, hash: {}, window: {}s", hash, currentWindow);
                                                localCacheService.put(hash, distributedCached);
                                                return auditService.recordDuplicateRequest(request, hash, fingerprint,
                                                                distributedCached, "distributed_cache", startTime)
                                                        .then(Mono.just(DeduplicationResult.duplicate(distributedCached, hash)));
                                            }

                                            return fingerprintLearningService.recordFingerprint(fingerprint, request, userId)
                                                    .then(auditService.recordFirstRequest(request, hash, fingerprint, startTime))
                                                    .then(Mono.just(DeduplicationResult.builder()
                                                            .isDuplicate(false)
                                                            .requestHash(hash)
                                                            .shouldProcess(true)
                                                            .fingerprint(fingerprint)
                                                            .build()));
                                        });
                            });
                });
    }

    public void cacheResponse(String requestHash, CachedResponse response) {
        if (requestHash == null || response == null) {
            return;
        }

        response.setRequestHash(requestHash);
        response.setTimestamp(System.currentTimeMillis());

        localCacheService.put(requestHash, response);
        quorumService.quorumSet(requestHash, response, properties.getCacheExpireSeconds())
                .doOnNext(success -> {
                    if (success) {
                        log.debug("Response cached with quorum, hash: {}", requestHash);
                    } else {
                        log.warn("Quorum write failed for hash: {}", requestHash);
                    }
                })
                .doOnError(e -> log.error("Failed to cache response with quorum", e))
                .subscribe();
    }

    public void releaseLock(String requestHash) {
        if (requestHash != null) {
            quorumService.quorumUnlock(requestHash).subscribe();
        }
    }

    public void performValidation(String requestHash, CachedResponse cachedResponse, CachedResponse actualResponse) {
        if (requestHash != null) {
            bypassValidationService.validateResponse(requestHash, cachedResponse, actualResponse).subscribe();
        }
    }

    public long getCurrentWindowSeconds() {
        return windowManager.getCurrentWindowSeconds();
    }

    public DynamicWindowManager.WindowStats getWindowStats() {
        return windowManager.getWindowStats();
    }

    public FingerprintLearningService.PatternStats getPatternStats() {
        return fingerprintLearningService.getPatternStats();
    }

    public AuditService.AuditStats getAuditStats() {
        return auditService.getAuditStats();
    }

    public BypassValidationService.ValidationStats getValidationStats() {
        return bypassValidationService.getValidationStats();
    }
}
