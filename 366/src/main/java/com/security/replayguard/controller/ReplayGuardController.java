package com.security.replayguard.controller;

import com.security.replayguard.attack.ActiveDefenseService;
import com.security.replayguard.attack.AttackEvent;
import com.security.replayguard.attack.AttackTraceService;
import com.security.replayguard.attack.AttackTrendAnalyzer;
import com.security.replayguard.core.ConsistentHashRouter;
import com.security.replayguard.core.DistributedCounter;
import com.security.replayguard.core.DualBufferSlidingWindowDetector;
import com.security.replayguard.core.DynamicHoneypotDetector;
import com.security.replayguard.core.HoneypotDetector;
import com.security.replayguard.core.ReplayGuardManager;
import com.security.replayguard.core.RequestHasher;
import com.security.replayguard.core.SlidingWindowDetector;
import com.security.replayguard.model.RequestFeature;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class ReplayGuardController {

    private final ReplayGuardManager replayGuardManager;
    private final RequestHasher requestHasher;
    private final SlidingWindowDetector slidingWindowDetector;
    private final DualBufferSlidingWindowDetector dualBufferSlidingWindowDetector;
    private final DistributedCounter distributedCounter;
    private final HoneypotDetector honeypotDetector;
    private final DynamicHoneypotDetector dynamicHoneypotDetector;
    private final ConsistentHashRouter consistentHashRouter;
    private final AttackTraceService attackTraceService;
    private final ActiveDefenseService activeDefenseService;
    private final AttackTrendAnalyzer attackTrendAnalyzer;

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "UP");
        result.put("service", "replay-guard");
        result.put("version", "2.0.0");
        result.put("features", Map.of(
                "userPartition", true,
                "dualBufferWindow", true,
                "dynamicHoneypot", true,
                "attackTrace", true,
                "activeDefense", true,
                "trendAnalysis", true
        ));
        return ResponseEntity.ok(result);
    }

    @PostMapping("/test/detect")
    public ResponseEntity<Map<String, Object>> testDetect(@RequestBody RequestFeature feature) {
        long startTime = System.currentTimeMillis();

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequest(feature);

        long duration = System.currentTimeMillis() - startTime;

        Map<String, Object> response = new HashMap<>();
        response.put("allowed", result.isAllowed());
        response.put("blocked", result.isBlocked());
        response.put("reason", result.getReason());
        response.put("requestHash", result.getRequestHash());
        response.put("targetNode", result.getTargetNode());
        response.put("partitionKey", result.getPartitionKey());
        response.put("detectionTimeMs", duration);

        return ResponseEntity.ok(response);
    }

    @GetMapping("/hash/compute")
    public ResponseEntity<Map<String, Object>> computeHash(
            @RequestParam String path,
            @RequestParam(required = false) String userId,
            @RequestParam(required = false) String fingerprint,
            @RequestParam(required = false) String timestamp,
            @RequestParam(required = false) String nonce) {

        RequestFeature feature = RequestFeature.builder()
                .requestPath(path)
                .userId(userId)
                .deviceFingerprint(fingerprint)
                .timestamp(timestamp)
                .nonce(nonce)
                .build();

        String uniqueHash = requestHasher.computeUniqueHash(feature);
        String hashWithUser = requestHasher.computeUniqueHashWithUser(feature);
        String fullHash = requestHasher.computeHash(feature);
        String partitionKey = requestHasher.computePartitionKey(feature);

        Map<String, Object> response = new HashMap<>();
        response.put("uniqueHash", uniqueHash);
        response.put("hashWithUser", hashWithUser);
        response.put("fullHash", fullHash);
        response.put("shortHash", requestHasher.computeShortHash(uniqueHash));
        response.put("partitionKey", partitionKey);
        response.put("targetNode", consistentHashRouter.getNode(hashWithUser));

        return ResponseEntity.ok(response);
    }

    @GetMapping("/partition/{userId}")
    public ResponseEntity<Map<String, Object>> getUserPartition(@PathVariable String userId) {
        String partitionKey = requestHasher.computeUserIdPartition(userId);
        long partitionCount = replayGuardManager.getUserPartitionCount(userId);

        Map<String, Object> response = new HashMap<>();
        response.put("userId", userId);
        response.put("partitionKey", partitionKey);
        response.put("requestCount", partitionCount);

        return ResponseEntity.ok(response);
    }

    @GetMapping("/sliding-window/count")
    public ResponseEntity<Map<String, Object>> getSlidingWindowCount(
            @RequestParam String hash,
            @RequestParam(defaultValue = "unknown") String partitionKey) {

        long count = dualBufferSlidingWindowDetector.getCurrentWindowCount(hash, partitionKey);

        Map<String, Object> response = new HashMap<>();
        response.put("hash", hash);
        response.put("partitionKey", partitionKey);
        response.put("currentWindowCount", count);
        response.put("targetNode", consistentHashRouter.getNode(hash));

        return ResponseEntity.ok(response);
    }

    @GetMapping("/sliding-window/status")
    public ResponseEntity<Map<String, Object>> getSlidingWindowStatus(
            @RequestParam String hash,
            @RequestParam(defaultValue = "unknown") String partitionKey) {

        DualBufferSlidingWindowDetector.WindowStatus status =
                dualBufferSlidingWindowDetector.getWindowStatus(hash, partitionKey);

        Map<String, Object> response = new HashMap<>();
        response.put("hash", hash);
        response.put("partitionKey", partitionKey);
        response.put("inOverlapPeriod", status.isInOverlapPeriod());
        response.put("needsWindowSwitch", status.isNeedsWindowSwitch());
        response.put("lastSwitchTime", status.getLastSwitchTime());
        response.put("currentWindowCount", status.getCurrentWindowCount());

        return ResponseEntity.ok(response);
    }

    @PostMapping("/sliding-window/switch")
    public ResponseEntity<Map<String, Object>> forceSwitchWindow(
            @RequestParam String hash,
            @RequestParam(defaultValue = "unknown") String partitionKey) {

        dualBufferSlidingWindowDetector.forceSwitchWindow(hash, partitionKey);

        Map<String, Object> response = new HashMap<>();
        response.put("hash", hash);
        response.put("partitionKey", partitionKey);
        response.put("status", "WINDOW_SWITCHED");

        return ResponseEntity.ok(response);
    }

    @GetMapping("/counter/{key}")
    public ResponseEntity<Map<String, Object>> getCounter(@PathVariable String key) {
        long count = distributedCounter.getCount(key);

        Map<String, Object> response = new HashMap<>();
        response.put("key", key);
        response.put("count", count);

        return ResponseEntity.ok(response);
    }

    @PostMapping("/counter/{key}/increment")
    public ResponseEntity<Map<String, Object>> incrementCounter(
            @PathVariable String key,
            @RequestParam(defaultValue = "100") long maxCount,
            @RequestParam(defaultValue = "60") int windowSeconds) {

        long count = distributedCounter.increment(key, maxCount, windowSeconds);

        Map<String, Object> response = new HashMap<>();
        response.put("key", key);
        response.put("currentCount", count);
        response.put("thresholdExceeded", count >= maxCount);

        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/counter/{key}")
    public ResponseEntity<Map<String, Object>> resetCounter(@PathVariable String key) {
        distributedCounter.reset(key);

        Map<String, Object> response = new HashMap<>();
        response.put("key", key);
        response.put("status", "RESET");

        return ResponseEntity.ok(response);
    }

    @GetMapping("/honeypot/status")
    public ResponseEntity<Map<String, Object>> getHoneypotStatus(@RequestParam String clientId) {
        boolean isBlocked = dynamicHoneypotDetector.isBlocked(clientId);
        long slowCount = dynamicHoneypotDetector.getSlowRequestCount(clientId);
        long currentThreshold = dynamicHoneypotDetector.getCurrentThreshold(clientId);

        Map<String, Object> response = new HashMap<>();
        response.put("clientId", clientId);
        response.put("blocked", isBlocked);
        response.put("slowRequestCount", slowCount);
        response.put("currentThresholdMs", currentThreshold);

        return ResponseEntity.ok(response);
    }

    @GetMapping("/honeypot/threshold-stats")
    public ResponseEntity<Map<String, Object>> getThresholdStats(@RequestParam String clientId) {
        DynamicHoneypotDetector.ThresholdStats stats =
                replayGuardManager.getThresholdStats(clientId);

        Map<String, Object> response = new HashMap<>();
        response.put("clientId", clientId);
        response.put("globalThresholdMs", stats.getGlobalThreshold());
        response.put("clientThresholdMs", stats.getClientThreshold());
        response.put("lastAdjustmentTime", stats.getLastAdjustmentTime());
        response.put("dynamicEnabled", stats.isDynamicEnabled());
        response.put("historySampleCount", stats.getHistorySampleCount());

        return ResponseEntity.ok(response);
    }

    @PostMapping("/honeypot/unblock")
    public ResponseEntity<Map<String, Object>> unblockClient(@RequestParam String clientId) {
        dynamicHoneypotDetector.unblock(clientId);
        replayGuardManager.resetClientState(clientId);

        Map<String, Object> response = new HashMap<>();
        response.put("clientId", clientId);
        response.put("status", "UNBLOCKED");

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/summary")
    public ResponseEntity<Map<String, Object>> getAttackSummary() {
        AttackTrendAnalyzer.AttackSummary summary = attackTrendAnalyzer.getSummary();

        Map<String, Object> response = new HashMap<>();
        response.put("totalAttacks", summary.getTotalAttacks());
        response.put("last24hAttacks", summary.getLast24hAttacks());
        response.put("last7dAttacks", summary.getLast7dAttacks());
        response.put("lastUpdateTime", summary.getLastUpdateTime());
        response.put("attackBreakdown", summary.getAttackBreakdown());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/ip/{ip}")
    public ResponseEntity<Map<String, Object>> getIpAttackStats(@PathVariable String ip) {
        AttackTraceService.AttackSourceStats stats = attackTraceService.getIpAttackStats(ip);

        Map<String, Object> response = new HashMap<>();
        response.put("ipAddress", stats.getIpAddress());
        response.put("totalAttacks", stats.getTotalAttacks());
        response.put("lastAttackTime", stats.getLastAttackTime());
        response.put("attackBreakdown", stats.getAttackBreakdown());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/user/{userId}")
    public ResponseEntity<Map<String, Object>> getUserAttackStats(@PathVariable String userId) {
        AttackTraceService.UserAttackStats stats = attackTraceService.getUserAttackStats(userId);

        Map<String, Object> response = new HashMap<>();
        response.put("userId", stats.getUserId());
        response.put("totalAttacks", stats.getTotalAttacks());
        response.put("lastAttackTime", stats.getLastAttackTime());
        response.put("attackBreakdown", stats.getAttackBreakdown());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/top-ips")
    public ResponseEntity<Map<String, Object>> getTopAttackIps(
            @RequestParam(defaultValue = "10") int limit) {
        List<AttackTraceService.AttackSourceStats> topIps = attackTraceService.getTopAttackIps(limit);

        Map<String, Object> response = new HashMap<>();
        response.put("topIps", topIps);
        response.put("count", topIps.size());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/recent")
    public ResponseEntity<Map<String, Object>> getRecentAttacks(
            @RequestParam(defaultValue = "20") int limit) {
        List<AttackEvent> attacks = attackTraceService.getRecentAttacks(limit);

        Map<String, Object> response = new HashMap<>();
        response.put("attacks", attacks);
        response.put("count", attacks.size());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/pattern/{attackType}")
    public ResponseEntity<Map<String, Object>> getAttackPattern(
            @PathVariable String attackType,
            @RequestParam(defaultValue = "24") int hours) {
        AttackTraceService.AttackPatternAnalysis pattern =
                attackTraceService.getPatternAnalysis(attackType, hours);

        Map<String, Object> response = new HashMap<>();
        response.put("attackType", pattern.getAttackType());
        response.put("totalAttacks", pattern.getTotalAttacks());
        response.put("peakHour", pattern.getPeakHour());
        response.put("averagePerHour", pattern.getAveragePerHour());
        response.put("hourlyDistribution", pattern.getHourlyDistribution());
        response.put("topTargetPaths", pattern.getTopTargetPaths());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/trend/hourly")
    public ResponseEntity<Map<String, Object>> getHourlyTrend(
            @RequestParam(defaultValue = "24") int hours) {
        AttackTrendAnalyzer.HourlyTrend trend = attackTrendAnalyzer.getHourlyTrend(hours);

        Map<String, Object> response = new HashMap<>();
        response.put("hours", trend.getHours());
        response.put("totalAttacks", trend.getTotalAttacks());
        response.put("averagePerHour", trend.getAveragePerHour());
        response.put("peakHourAttacks", trend.getPeakHourAttacks());
        response.put("stdDeviation", trend.getStdDeviation());
        response.put("hourlyStats", trend.getHourlyStats());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/trend/daily")
    public ResponseEntity<Map<String, Object>> getDailyTrend(
            @RequestParam(defaultValue = "7") int days) {
        AttackTrendAnalyzer.DailyTrend trend = attackTrendAnalyzer.getDailyTrend(days);

        Map<String, Object> response = new HashMap<>();
        response.put("days", trend.getDays());
        response.put("totalAttacks", trend.getTotalAttacks());
        response.put("averagePerDay", trend.getAveragePerDay());
        response.put("dailyStats", trend.getDailyStats());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/attack/time-pattern")
    public ResponseEntity<Map<String, Object>> getTimePatternAnalysis(
            @RequestParam(defaultValue = "24") int hours) {
        AttackTrendAnalyzer.TimePatternAnalysis analysis = attackTrendAnalyzer.analyzeTimePatterns(hours);

        Map<String, Object> response = new HashMap<>();
        response.put("hourOfDayDistribution", analysis.getHourOfDayDistribution());
        response.put("peakHours", analysis.getPeakHours());
        response.put("quietHours", analysis.getQuietHours());
        response.put("maxConsecutiveIncreases", analysis.getMaxConsecutiveIncreases());
        response.put("attackRatePerHour", analysis.getAttackRatePerHour());
        response.put("trendDirection", analysis.getTrendDirection());
        response.put("trendingUp", analysis.isTrendingUp());
        response.put("trendingDown", analysis.isTrendingDown());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/defense/account/{userId}")
    public ResponseEntity<Map<String, Object>> getAccountLockStatus(@PathVariable String userId) {
        ActiveDefenseService.AccountLockStatus status = activeDefenseService.getAccountLockStatus(userId);

        Map<String, Object> response = new HashMap<>();
        response.put("userId", status.getUserId());
        response.put("locked", status.isLocked());
        if (status.isLocked()) {
            response.put("reason", status.getReason());
            response.put("lockTime", status.getLockTime());
            response.put("durationSeconds", status.getDurationSeconds());
            response.put("remainingSeconds", status.getRemainingSeconds());
        }

        return ResponseEntity.ok(response);
    }

    @GetMapping("/defense/ip/{ip}")
    public ResponseEntity<Map<String, Object>> getIpLockStatus(@PathVariable String ip) {
        ActiveDefenseService.IpLockStatus status = activeDefenseService.getIpLockStatus(ip);

        Map<String, Object> response = new HashMap<>();
        response.put("ipAddress", status.getIpAddress());
        response.put("locked", status.isLocked());
        if (status.isLocked()) {
            response.put("reason", status.getReason());
            response.put("lockTime", status.getLockTime());
            response.put("durationSeconds", status.getDurationSeconds());
            response.put("remainingSeconds", status.getRemainingSeconds());
        }

        return ResponseEntity.ok(response);
    }

    @PostMapping("/defense/account/{userId}/lock")
    public ResponseEntity<Map<String, Object>> lockAccount(
            @PathVariable String userId,
            @RequestParam(defaultValue = "1800") int durationSeconds,
            @RequestParam(defaultValue = "Manual lock") String reason) {
        activeDefenseService.lockAccount(userId, durationSeconds, reason);

        Map<String, Object> response = new HashMap<>();
        response.put("userId", userId);
        response.put("status", "LOCKED");
        response.put("durationSeconds", durationSeconds);
        response.put("reason", reason);

        return ResponseEntity.ok(response);
    }

    @PostMapping("/defense/ip/{ip}/lock")
    public ResponseEntity<Map<String, Object>> lockIp(
            @PathVariable String ip,
            @RequestParam(defaultValue = "3600") int durationSeconds,
            @RequestParam(defaultValue = "Manual lock") String reason) {
        activeDefenseService.lockIp(ip, durationSeconds, reason);

        Map<String, Object> response = new HashMap<>();
        response.put("ipAddress", ip);
        response.put("status", "LOCKED");
        response.put("durationSeconds", durationSeconds);
        response.put("reason", reason);

        return ResponseEntity.ok(response);
    }

    @PostMapping("/defense/account/{userId}/unlock")
    public ResponseEntity<Map<String, Object>> unlockAccount(@PathVariable String userId) {
        activeDefenseService.unlockAccount(userId);

        Map<String, Object> response = new HashMap<>();
        response.put("userId", userId);
        response.put("status", "UNLOCKED");

        return ResponseEntity.ok(response);
    }

    @PostMapping("/defense/ip/{ip}/unlock")
    public ResponseEntity<Map<String, Object>> unlockIp(@PathVariable String ip) {
        activeDefenseService.unlockIp(ip);

        Map<String, Object> response = new HashMap<>();
        response.put("ipAddress", ip);
        response.put("status", "UNLOCKED");

        return ResponseEntity.ok(response);
    }

    @GetMapping("/defense/locked-accounts")
    public ResponseEntity<Map<String, Object>> getLockedAccounts() {
        Set<String> lockedAccounts = activeDefenseService.getLockedAccounts();

        Map<String, Object> response = new HashMap<>();
        response.put("lockedAccounts", lockedAccounts);
        response.put("count", lockedAccounts.size());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/defense/locked-ips")
    public ResponseEntity<Map<String, Object>> getLockedIps() {
        Set<String> lockedIps = activeDefenseService.getLockedIps();

        Map<String, Object> response = new HashMap<>();
        response.put("lockedIps", lockedIps);
        response.put("count", lockedIps.size());

        return ResponseEntity.ok(response);
    }

    @GetMapping("/consistent-hash/nodes")
    public ResponseEntity<Map<String, Object>> getConsistentHashNodes() {
        Set<String> nodes = consistentHashRouter.getAllNodes();
        Map<String, Integer> distribution = consistentHashRouter.getNodeDistribution();

        Map<String, Object> response = new HashMap<>();
        response.put("nodes", nodes);
        response.put("nodeCount", nodes.size());
        response.put("distribution", distribution);

        return ResponseEntity.ok(response);
    }

    @GetMapping("/consistent-hash/route")
    public ResponseEntity<Map<String, Object>> getRoute(@RequestParam String key,
                                                        @RequestParam(defaultValue = "1") int replicas) {
        String primaryNode = consistentHashRouter.getNode(key);
        var nodes = consistentHashRouter.getNodes(key, replicas);

        Map<String, Object> response = new HashMap<>();
        response.put("key", key);
        response.put("primaryNode", primaryNode);
        response.put("replicaNodes", nodes);

        return ResponseEntity.ok(response);
    }
}
