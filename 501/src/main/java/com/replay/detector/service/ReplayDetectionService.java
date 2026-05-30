package com.replay.detector.service;

import com.replay.detector.config.ReplayDetectionProperties;
import com.replay.detector.model.DetectionResult;
import com.replay.detector.model.ReplayAlert;
import com.replay.detector.model.RequestFingerprint;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReplayDetectionService {

    private final FingerprintService fingerprintService;
    private final BloomFilterService bloomFilterService;
    private final SlidingWindowService slidingWindowService;
    private final DistributedLockService distributedLockService;
    private final WebhookAlertService webhookAlertService;
    private final AttackTracingService attackTracingService;
    private final AdaptiveThresholdService adaptiveThresholdService;
    private final TrendAnalysisService trendAnalysisService;
    private final ReplayDetectionProperties properties;

    public DetectionResult detect(String requestId, String path, java.util.Map<String, String> params,
                                  String userAgent, String clientIp, String httpMethod, long timestamp) {
        if (!properties.isEnabled()) {
            return DetectionResult.safe("disabled", 0, 0);
        }

        adaptiveThresholdService.recordRequest();

        RequestFingerprint fingerprint = fingerprintService.buildFingerprint(
                requestId, path, params, userAgent, clientIp, httpMethod, timestamp);

        String hash = fingerprint.getFingerprintHash();
        log.debug("Processing request fingerprint: hash={}, path={}, clientIp={}", hash, path, clientIp);

        attackTracingService.recordDeviceFingerprint(clientIp, userAgent);

        if (bloomFilterService.mightContainLocal(hash)) {
            log.debug("Local bloom filter hit for hash: {}", hash);

            boolean distributedHit = bloomFilterService.checkDistributed(hash);
            if (distributedHit) {
                boolean confirmed = bloomFilterService.confirmHit(hash);
                if (!confirmed) {
                    log.info("Bloom filter hit not confirmed (false positive), treating as new request: hash={}", hash);
                    return handleNewRequest(hash, fingerprint);
                }

                int effectiveMaxCount = adaptiveThresholdService.getAdaptiveMaxReplayCount();
                SlidingWindowService.SlidingWindowResult windowResult = slidingWindowService.recordAndCheck(
                        hash, properties.getWindowSizeSeconds(), effectiveMaxCount);

                if (windowResult.isReplay()) {
                    log.warn("Replay attack detected: hash={}, count={}, adaptiveThreshold={}, overlap={}",
                            hash, windowResult.count(), effectiveMaxCount, windowResult.overlapActive());

                    attackTracingService.recordAttack(fingerprint, windowResult.count());
                    trendAnalysisService.recordAttackEvent(clientIp, path, hash, windowResult.count());

                    DetectionResult result = DetectionResult.replay(
                            hash, windowResult.count(),
                            windowResult.windowStart(),
                            windowResult.windowStart() + properties.getWindowSizeSeconds() * 1000L);

                    ReplayAlert alert = buildAlert(fingerprint, windowResult.count());
                    webhookAlertService.sendAlert(alert);

                    return result;
                }

                return DetectionResult.safe(hash, windowResult.windowStart(),
                        windowResult.windowStart() + properties.getWindowSizeSeconds() * 1000L);
            }
        }

        return handleNewRequest(hash, fingerprint);
    }

    private DetectionResult handleNewRequest(String hash, RequestFingerprint fingerprint) {
        String lockValue = distributedLockService.tryLock(hash);
        if (lockValue == null) {
            log.debug("Could not acquire lock, processing without lock: hash={}", hash);
            bloomFilterService.putLocal(hash);
            bloomFilterService.checkAndMarkDistributed(hash);
            slidingWindowService.recordAndCheck(hash);
            return DetectionResult.safe(hash, System.currentTimeMillis() - properties.getWindowSizeSeconds() * 1000L,
                    System.currentTimeMillis());
        }

        try {
            bloomFilterService.putLocal(hash);
            bloomFilterService.checkAndMarkDistributed(hash);

            int effectiveMaxCount = adaptiveThresholdService.getAdaptiveMaxReplayCount();
            SlidingWindowService.SlidingWindowResult windowResult = slidingWindowService.recordAndCheck(
                    hash, properties.getWindowSizeSeconds(), effectiveMaxCount);

            if (windowResult.isReplay()) {
                log.warn("Replay attack detected after lock: hash={}, count={}, adaptiveThreshold={}, overlap={}",
                        hash, windowResult.count(), effectiveMaxCount, windowResult.overlapActive());

                attackTracingService.recordAttack(fingerprint, windowResult.count());
                trendAnalysisService.recordAttackEvent(fingerprint.getClientIp(), fingerprint.getPath(), hash, windowResult.count());

                DetectionResult result = DetectionResult.replay(
                        hash, windowResult.count(),
                        windowResult.windowStart(),
                        windowResult.windowStart() + properties.getWindowSizeSeconds() * 1000L);

                ReplayAlert alert = buildAlert(fingerprint, windowResult.count());
                webhookAlertService.sendAlert(alert);

                return result;
            }

            return DetectionResult.safe(hash, windowResult.windowStart(),
                    windowResult.windowStart() + properties.getWindowSizeSeconds() * 1000L);

        } finally {
            distributedLockService.releaseLock(hash, lockValue);
        }
    }

    public DetectionResult detectWithCustomWindow(String requestId, String path,
                                                   java.util.Map<String, String> params,
                                                   String userAgent, String clientIp,
                                                   String httpMethod, long timestamp,
                                                   int windowSizeSeconds, int maxReplayCount) {
        if (!properties.isEnabled()) {
            return DetectionResult.safe("disabled", 0, 0);
        }

        adaptiveThresholdService.recordRequest();

        RequestFingerprint fingerprint = fingerprintService.buildFingerprint(
                requestId, path, params, userAgent, clientIp, httpMethod, timestamp);

        String hash = fingerprint.getFingerprintHash();

        attackTracingService.recordDeviceFingerprint(clientIp, userAgent);

        SlidingWindowService.SlidingWindowResult windowResult =
                slidingWindowService.recordAndCheck(hash, windowSizeSeconds, maxReplayCount);

        if (windowResult.isReplay()) {
            attackTracingService.recordAttack(fingerprint, windowResult.count());
            trendAnalysisService.recordAttackEvent(clientIp, path, hash, windowResult.count());

            DetectionResult result = DetectionResult.replay(
                    hash, windowResult.count(),
                    windowResult.windowStart(),
                    windowResult.windowStart() + windowSizeSeconds * 1000L);

            ReplayAlert alert = buildAlert(fingerprint, windowResult.count());
            webhookAlertService.sendAlert(alert);

            return result;
        }

        return DetectionResult.safe(hash, windowResult.windowStart(),
                windowResult.windowStart() + windowSizeSeconds * 1000L);
    }

    private ReplayAlert buildAlert(RequestFingerprint fingerprint, int replayCount) {
        ReplayAlert.AlertLevel level = determineAlertLevel(replayCount);

        return ReplayAlert.builder()
                .alertId(java.util.UUID.randomUUID().toString())
                .level(level)
                .fingerprintHash(fingerprint.getFingerprintHash())
                .path(fingerprint.getPath())
                .clientIp(fingerprint.getClientIp())
                .replayCount(replayCount)
                .windowSizeSeconds(properties.getWindowSizeSeconds())
                .detectedAt(System.currentTimeMillis())
                .message(String.format("Replay attack detected from IP %s on path %s: %d requests in %d seconds window",
                        fingerprint.getClientIp(), fingerprint.getPath(), replayCount, properties.getWindowSizeSeconds()))
                .build();
    }

    private ReplayAlert.AlertLevel determineAlertLevel(int replayCount) {
        int threshold = adaptiveThresholdService.getAdaptiveMaxReplayCount();
        if (replayCount >= threshold * 4) {
            return ReplayAlert.AlertLevel.CRITICAL;
        } else if (replayCount >= threshold * 3) {
            return ReplayAlert.AlertLevel.HIGH;
        } else if (replayCount >= threshold * 2) {
            return ReplayAlert.AlertLevel.MEDIUM;
        }
        return ReplayAlert.AlertLevel.LOW;
    }
}
