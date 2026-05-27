package com.security.replayguard.attack;

import com.security.replayguard.config.ReplayGuardProperties;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
public class ActiveDefenseService {

    private static final String ACCOUNT_LOCK_PREFIX = "replay:lock:account:";
    private static final String IP_LOCK_PREFIX = "replay:lock:ip:";
    private static final String ATTACK_THRESHOLD_PREFIX = "replay:defense:threshold:";
    private static final String LOCK_HISTORY_PREFIX = "replay:lock:history:";

    private final StringRedisTemplate redisTemplate;
    private final ReplayGuardProperties properties;
    private final AttackTraceService attackTraceService;

    public LockResult checkAndLockAccount(String userId, String ipAddress) {
        if (isAccountLocked(userId)) {
            return new LockResult(true, getLockReason(userId), getLockRemainingTime(userId));
        }

        if (isIpLocked(ipAddress)) {
            return new LockResult(true, getIpLockReason(ipAddress), getIpLockRemainingTime(ipAddress));
        }

        AttackTraceService.UserAttackStats userStats = attackTraceService.getUserAttackStats(userId);
        AttackTraceService.AttackSourceStats ipStats = attackTraceService.getIpAttackStats(ipAddress);

        LockPolicy policy = getLockPolicy();

        if (userStats.getTotalAttacks() >= policy.getUserAttackThreshold()) {
            lockAccount(userId, policy.getAccountLockDurationSeconds(),
                    "Attack threshold exceeded: " + userStats.getTotalAttacks() + " attacks");
            log.warn("Account locked: userId={}, attacks={}, duration={}s",
                    userId, userStats.getTotalAttacks(), policy.getAccountLockDurationSeconds());
            return new LockResult(true, "Attack threshold exceeded", policy.getAccountLockDurationSeconds());
        }

        if (ipStats.getTotalAttacks() >= policy.getIpAttackThreshold()) {
            lockIp(ipAddress, policy.getIpLockDurationSeconds(),
                    "IP attack threshold exceeded: " + ipStats.getTotalAttacks() + " attacks");
            log.warn("IP locked: ip={}, attacks={}, duration={}s",
                    ipAddress, ipStats.getTotalAttacks(), policy.getIpLockDurationSeconds());
            return new LockResult(true, "IP attack threshold exceeded", policy.getIpLockDurationSeconds());
        }

        return new LockResult(false, null, 0);
    }

    public void lockAccount(String userId, int durationSeconds, String reason) {
        String lockKey = ACCOUNT_LOCK_PREFIX + userId;
        Map<String, String> lockData = new HashMap<>();
        lockData.put("locked", "true");
        lockData.put("reason", reason);
        lockData.put("lockTime", String.valueOf(System.currentTimeMillis() / 1000));
        lockData.put("duration", String.valueOf(durationSeconds));

        redisTemplate.opsForHash().putAll(lockKey, lockData);
        redisTemplate.expire(lockKey, durationSeconds, TimeUnit.SECONDS);

        recordLockHistory("account", userId, reason, durationSeconds);
    }

    public void lockIp(String ipAddress, int durationSeconds, String reason) {
        String lockKey = IP_LOCK_PREFIX + ipAddress;
        Map<String, String> lockData = new HashMap<>();
        lockData.put("locked", "true");
        lockData.put("reason", reason);
        lockData.put("lockTime", String.valueOf(System.currentTimeMillis() / 1000));
        lockData.put("duration", String.valueOf(durationSeconds));

        redisTemplate.opsForHash().putAll(lockKey, lockData);
        redisTemplate.expire(lockKey, durationSeconds, TimeUnit.SECONDS);

        recordLockHistory("ip", ipAddress, reason, durationSeconds);
    }

    public boolean isAccountLocked(String userId) {
        if (userId == null || userId.isEmpty()) {
            return false;
        }
        String lockKey = ACCOUNT_LOCK_PREFIX + userId;
        return Boolean.TRUE.equals(redisTemplate.hasKey(lockKey));
    }

    public boolean isIpLocked(String ipAddress) {
        if (ipAddress == null || ipAddress.isEmpty()) {
            return false;
        }
        String lockKey = IP_LOCK_PREFIX + ipAddress;
        return Boolean.TRUE.equals(redisTemplate.hasKey(lockKey));
    }

    public String getLockReason(String userId) {
        String lockKey = ACCOUNT_LOCK_PREFIX + userId;
        Object reason = redisTemplate.opsForHash().get(lockKey, "reason");
        return reason != null ? reason.toString() : null;
    }

    public String getIpLockReason(String ipAddress) {
        String lockKey = IP_LOCK_PREFIX + ipAddress;
        Object reason = redisTemplate.opsForHash().get(lockKey, "reason");
        return reason != null ? reason.toString() : null;
    }

    public long getLockRemainingTime(String userId) {
        String lockKey = ACCOUNT_LOCK_PREFIX + userId;
        Long ttl = redisTemplate.getExpire(lockKey, TimeUnit.SECONDS);
        return ttl != null ? ttl : 0;
    }

    public long getIpLockRemainingTime(String ipAddress) {
        String lockKey = IP_LOCK_PREFIX + ipAddress;
        Long ttl = redisTemplate.getExpire(lockKey, TimeUnit.SECONDS);
        return ttl != null ? ttl : 0;
    }

    public void unlockAccount(String userId) {
        String lockKey = ACCOUNT_LOCK_PREFIX + userId;
        redisTemplate.delete(lockKey);
        log.info("Account unlocked: userId={}", userId);
    }

    public void unlockIp(String ipAddress) {
        String lockKey = IP_LOCK_PREFIX + ipAddress;
        redisTemplate.delete(lockKey);
        log.info("IP unlocked: ip={}", ipAddress);
    }

    public AccountLockStatus getAccountLockStatus(String userId) {
        AccountLockStatus status = new AccountLockStatus();
        status.setUserId(userId);

        if (!isAccountLocked(userId)) {
            status.setLocked(false);
            return status;
        }

        String lockKey = ACCOUNT_LOCK_PREFIX + userId;
        Map<Object, Object> data = redisTemplate.opsForHash().entries(lockKey);

        status.setLocked(true);
        status.setReason((String) data.get("reason"));
        status.setLockTime(parseLong(data.get("lockTime")));
        status.setDurationSeconds(parseLong(data.get("duration")));
        status.setRemainingSeconds(getLockRemainingTime(userId));

        return status;
    }

    public IpLockStatus getIpLockStatus(String ipAddress) {
        IpLockStatus status = new IpLockStatus();
        status.setIpAddress(ipAddress);

        if (!isIpLocked(ipAddress)) {
            status.setLocked(false);
            return status;
        }

        String lockKey = IP_LOCK_PREFIX + ipAddress;
        Map<Object, Object> data = redisTemplate.opsForHash().entries(lockKey);

        status.setLocked(true);
        status.setReason((String) data.get("reason"));
        status.setLockTime(parseLong(data.get("lockTime")));
        status.setDurationSeconds(parseLong(data.get("duration")));
        status.setRemainingSeconds(getIpLockRemainingTime(ipAddress));

        return status;
    }

    public Set<String> getLockedAccounts() {
        Set<String> keys = redisTemplate.keys(ACCOUNT_LOCK_PREFIX + "*");
        if (keys == null) {
            return java.util.Collections.emptySet();
        }
        return keys.stream()
                .map(k -> k.substring(ACCOUNT_LOCK_PREFIX.length()))
                .collect(Collectors.toSet());
    }

    public Set<String> getLockedIps() {
        Set<String> keys = redisTemplate.keys(IP_LOCK_PREFIX + "*");
        if (keys == null) {
            return java.util.Collections.emptySet();
        }
        return keys.stream()
                .map(k -> k.substring(IP_LOCK_PREFIX.length()))
                .collect(Collectors.toSet());
    }

    private void recordLockHistory(String type, String target, String reason, int durationSeconds) {
        String historyKey = LOCK_HISTORY_PREFIX + type + ":" + target;
        long lockTime = System.currentTimeMillis() / 1000;

        Map<String, String> record = new HashMap<>();
        record.put("type", type);
        record.put("target", target);
        record.put("reason", reason);
        record.put("duration", String.valueOf(durationSeconds));
        record.put("time", String.valueOf(lockTime));

        redisTemplate.opsForZSet().add(historyKey,
                lockTime + ":" + reason,
                lockTime);
        redisTemplate.expire(historyKey, 30, TimeUnit.DAYS);
    }

    private LockPolicy getLockPolicy() {
        LockPolicy policy = new LockPolicy();
        policy.setUserAttackThreshold(10);
        policy.setIpAttackThreshold(50);
        policy.setAccountLockDurationSeconds(1800);
        policy.setIpLockDurationSeconds(3600);
        return policy;
    }

    private long parseLong(Object value) {
        if (value == null) {
            return 0;
        }
        try {
            return Long.parseLong(value.toString());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    @Data
    public static class LockResult {
        private final boolean locked;
        private final String reason;
        private final long durationSeconds;
    }

    @Data
    public static class LockPolicy {
        private int userAttackThreshold;
        private int ipAttackThreshold;
        private int accountLockDurationSeconds;
        private int ipLockDurationSeconds;
    }

    @Data
    public static class AccountLockStatus {
        private String userId;
        private boolean locked;
        private String reason;
        private long lockTime;
        private long durationSeconds;
        private long remainingSeconds;
    }

    @Data
    public static class IpLockStatus {
        private String ipAddress;
        private boolean locked;
        private String reason;
        private long lockTime;
        private long durationSeconds;
        private long remainingSeconds;
    }
}
