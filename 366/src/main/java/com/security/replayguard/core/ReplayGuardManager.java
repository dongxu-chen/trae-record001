package com.security.replayguard.core;

import com.security.replayguard.attack.ActiveDefenseService;
import com.security.replayguard.attack.AttackEvent;
import com.security.replayguard.attack.AttackTraceService;
import com.security.replayguard.attack.AttackTrendAnalyzer;
import com.security.replayguard.config.ReplayGuardProperties;
import com.security.replayguard.model.RequestFeature;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class ReplayGuardManager {

    private final RequestHasher requestHasher;
    private final SlidingWindowDetector slidingWindowDetector;
    private final DualBufferSlidingWindowDetector dualBufferSlidingWindowDetector;
    private final NonceDetector nonceDetector;
    private final DistributedCounter distributedCounter;
    private final HoneypotDetector honeypotDetector;
    private final DynamicHoneypotDetector dynamicHoneypotDetector;
    private final ConsistentHashRouter consistentHashRouter;
    private final ReplayGuardProperties properties;
    private final AttackTraceService attackTraceService;
    private final ActiveDefenseService activeDefenseService;
    private final AttackTrendAnalyzer attackTrendAnalyzer;

    public DetectionResult checkRequest(RequestFeature feature) {
        DetectionResult result = new DetectionResult();
        result.setRequestFeature(feature);

        String partitionKey = requestHasher.computePartitionKey(feature);
        result.setPartitionKey(partitionKey);

        String clientIdentifier = getClientIdentifier(feature);

        ActiveDefenseService.LockResult lockResult =
                activeDefenseService.checkAndLockAccount(clientIdentifier, feature.getIpAddress());

        if (lockResult.isLocked()) {
            result.setBlocked(true);
            result.setReason("ACCOUNT_OR_IP_LOCKED: " + lockResult.getReason());
            log.warn("Request blocked by active defense: userId={}, ip={}, reason={}",
                    clientIdentifier, feature.getIpAddress(), lockResult.getReason());

            recordAttack(feature, AttackEvent.AttackType.RATE_LIMIT_BREACH.getCode(),
                    "Account/IP locked: " + lockResult.getReason(), partitionKey);
            return result;
        }

        if (dynamicHoneypotDetector.isBlocked(clientIdentifier)) {
            result.setBlocked(true);
            result.setReason("CLIENT_BLOCKED_BY_HONEYPOT");
            log.warn("Request blocked by honeypot: {}, partition: {}", clientIdentifier, partitionKey);

            recordAttack(feature, AttackEvent.AttackType.HONEYPOT_TRIGGERED.getCode(),
                    "Client blocked by honeypot", partitionKey);
            return result;
        }

        String timestamp = feature.getTimestamp();
        if (timestamp != null && !timestamp.isEmpty()) {
            boolean validTimestamp = nonceDetector.validateTimestamp(timestamp, 300);
            if (!validTimestamp) {
                result.setBlocked(true);
                result.setReason("INVALID_TIMESTAMP");
                log.warn("Request with invalid timestamp: {}, partition: {}", timestamp, partitionKey);

                recordAttack(feature, AttackEvent.AttackType.INVALID_TIMESTAMP.getCode(),
                        "Invalid timestamp: " + timestamp, partitionKey);
                return result;
            }
        }

        if (feature.getNonce() != null && !feature.getNonce().isEmpty()) {
            boolean isReplay = nonceDetector.isReplayAttack(
                    feature.getDeviceFingerprint(),
                    feature.getNonce(),
                    feature.getTimestamp()
            );

            if (isReplay) {
                result.setBlocked(true);
                result.setReason("NONCE_REPLAY_DETECTED");
                log.warn("Nonce replay attack detected for client: {}, partition: {}", clientIdentifier, partitionKey);

                recordAttack(feature, AttackEvent.AttackType.NONCE_REPLAY.getCode(),
                        "Nonce replay detected", partitionKey);
                return result;
            }
        }

        String uniqueHash = requestHasher.computeUniqueHashWithUser(feature);
        result.setRequestHash(uniqueHash);

        String targetNode = consistentHashRouter.getNode(uniqueHash);
        result.setTargetNode(targetNode);

        boolean slidingWindowAllowed;
        if (properties.getSlidingWindow().isDualBufferEnabled()) {
            slidingWindowAllowed = dualBufferSlidingWindowDetector.isAllowed(uniqueHash, partitionKey);
        } else {
            slidingWindowAllowed = slidingWindowDetector.isAllowed(uniqueHash);
        }

        if (!slidingWindowAllowed) {
            result.setBlocked(true);
            result.setReason("SLIDING_WINDOW_LIMIT_EXCEEDED");
            log.warn("Sliding window limit exceeded for hash: {}, partition: {}, node: {}",
                    uniqueHash, partitionKey, targetNode);

            recordAttack(feature, AttackEvent.AttackType.SLIDING_WINDOW_BREACH.getCode(),
                    "Sliding window limit exceeded", partitionKey);
            return result;
        }

        String counterKey = partitionKey + ":" + clientIdentifier;
        long counterValue = distributedCounter.increment(counterKey, 1000, 60);
        if (counterValue > 1000) {
            result.setBlocked(true);
            result.setReason("RATE_LIMIT_EXCEEDED");
            log.warn("Rate limit exceeded for client: {}, partition: {}, count: {}",
                    clientIdentifier, partitionKey, counterValue);

            recordAttack(feature, AttackEvent.AttackType.RATE_LIMIT_BREACH.getCode(),
                    "Rate limit exceeded: " + counterValue, partitionKey);
            return result;
        }

        result.setAllowed(true);
        return result;
    }

    public DetectionResult checkRequestWithHoneypot(RequestFeature feature, long requestTimeMs) {
        DetectionResult result = checkRequest(feature);

        if (!result.isBlocked()) {
            String clientIdentifier = getClientIdentifier(feature);

            DynamicHoneypotDetector.HoneypotResult honeypotResult =
                    dynamicHoneypotDetector.check(clientIdentifier, requestTimeMs);

            if (honeypotResult.isBlocked()) {
                result.setBlocked(true);
                result.setReason("HONEYPOT_TRIGGERED");
                log.warn("Honeypot triggered for client: {}, partition: {}",
                        clientIdentifier, result.getPartitionKey());

                recordAttack(feature, AttackEvent.AttackType.HONEYPOT_TRIGGERED.getCode(),
                        "Honeypot triggered, request time: " + requestTimeMs + "ms",
                        result.getPartitionKey());
            }
        }

        return result;
    }

    private void recordAttack(RequestFeature feature, String attackType, String reason, String partitionKey) {
        try {
            AttackEvent event = AttackEvent.builder()
                    .attackType(attackType)
                    .ipAddress(feature.getIpAddress())
                    .userId(feature.getUserId())
                    .deviceFingerprint(feature.getDeviceFingerprint())
                    .requestPath(feature.getRequestPath())
                    .requestHash(requestHasher.computeUniqueHashWithUser(feature))
                    .reason(reason)
                    .sourceNode(partitionKey)
                    .build();

            attackTraceService.recordAttack(event);
            attackTrendAnalyzer.recordAttackEvent(attackType, feature.getIpAddress(), feature.getUserId());
        } catch (Exception e) {
            log.error("Failed to record attack event", e);
        }
    }

    private String getClientIdentifier(RequestFeature feature) {
        String userId = feature.getUserId();
        if (userId != null && !userId.isEmpty()) {
            return userId;
        }

        String fp = feature.getDeviceFingerprint();
        String ip = feature.getIpAddress();
        return (fp != null && !fp.isEmpty()) ? fp : (ip != null ? ip : "unknown");
    }

    public String getNodeForHash(String hash) {
        return consistentHashRouter.getNode(hash);
    }

    public void resetClientState(String clientIdentifier) {
        dynamicHoneypotDetector.unblock(clientIdentifier);
        distributedCounter.reset(clientIdentifier);
        activeDefenseService.unlockAccount(clientIdentifier);
        log.info("Reset state for client: {}", clientIdentifier);
    }

    public DynamicHoneypotDetector.ThresholdStats getThresholdStats(String clientIdentifier) {
        return dynamicHoneypotDetector.getThresholdStats(clientIdentifier);
    }

    public DualBufferSlidingWindowDetector.WindowStatus getWindowStatus(String uniqueHash, String partitionKey) {
        return dualBufferSlidingWindowDetector.getWindowStatus(uniqueHash, partitionKey);
    }

    public long getUserPartitionCount(String userId) {
        String partitionKey = requestHasher.computeUserIdPartition(userId);
        return distributedCounter.getCount(partitionKey);
    }

    public AttackTraceService getAttackTraceService() {
        return attackTraceService;
    }

    public ActiveDefenseService getActiveDefenseService() {
        return activeDefenseService;
    }

    public AttackTrendAnalyzer getAttackTrendAnalyzer() {
        return attackTrendAnalyzer;
    }

    public static class DetectionResult {
        private boolean allowed;
        private boolean blocked;
        private String reason;
        private String requestHash;
        private String targetNode;
        private String partitionKey;
        private RequestFeature requestFeature;

        public boolean isAllowed() {
            return allowed;
        }

        public void setAllowed(boolean allowed) {
            this.allowed = allowed;
        }

        public boolean isBlocked() {
            return blocked;
        }

        public void setBlocked(boolean blocked) {
            this.blocked = blocked;
        }

        public String getReason() {
            return reason;
        }

        public void setReason(String reason) {
            this.reason = reason;
        }

        public String getRequestHash() {
            return requestHash;
        }

        public void setRequestHash(String requestHash) {
            this.requestHash = requestHash;
        }

        public String getTargetNode() {
            return targetNode;
        }

        public void setTargetNode(String targetNode) {
            this.targetNode = targetNode;
        }

        public String getPartitionKey() {
            return partitionKey;
        }

        public void setPartitionKey(String partitionKey) {
            this.partitionKey = partitionKey;
        }

        public RequestFeature getRequestFeature() {
            return requestFeature;
        }

        public void setRequestFeature(RequestFeature requestFeature) {
            this.requestFeature = requestFeature;
        }
    }
}
