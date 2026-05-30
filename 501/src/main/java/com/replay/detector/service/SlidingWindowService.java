package com.replay.detector.service;

import com.replay.detector.config.ReplayDetectionProperties;
import com.replay.detector.model.WindowStats;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
public class SlidingWindowService {

    private final StringRedisTemplate redisTemplate;
    private final ReplayDetectionProperties properties;

    private static final String DUAL_WINDOW_SCRIPT =
            "local currentKey = KEYS[1] " +
            "local previousKey = KEYS[2] " +
            "local now = tonumber(ARGV[1]) " +
            "local window = tonumber(ARGV[2]) " +
            "local member = ARGV[3] " +
            "local maxCount = tonumber(ARGV[4]) " +
            "local overlap = tonumber(ARGV[5]) " +
            "local halfWindow = math.floor(window / 2) " +
            "local currentEpoch = math.floor(now / (halfWindow * 1000)) " +
            "local effectiveCurrentKey = currentKey .. ':e:' .. currentEpoch " +
            "local effectivePreviousKey = previousKey .. ':e:' .. (currentEpoch - 1) " +
            "local windowStart = now - window * 1000 " +
            "redis.call('ZREMRANGEBYSCORE', effectiveCurrentKey, '-inf', windowStart) " +
            "redis.call('ZREMRANGEBYSCORE', effectivePreviousKey, '-inf', windowStart) " +
            "local prevCount = redis.call('ZCARD', effectivePreviousKey) " +
            "local isOverlap = 0 " +
            "if prevCount > 0 then isOverlap = 1 end " +
            "redis.call('ZADD', effectiveCurrentKey, now, member .. ':' .. now) " +
            "redis.call('EXPIRE', effectiveCurrentKey, window + halfWindow + 1) " +
            "redis.call('EXPIRE', effectivePreviousKey, window + 1) " +
            "local currentCount = redis.call('ZCARD', effectiveCurrentKey) " +
            "local totalCount = currentCount + prevCount " +
            "local isReplay = 0 " +
            "if totalCount > maxCount then isReplay = 1 end " +
            "return {totalCount, isReplay, windowStart, currentCount, prevCount, isOverlap, currentEpoch} ";

    public SlidingWindowService(StringRedisTemplate redisTemplate, ReplayDetectionProperties properties) {
        this.redisTemplate = redisTemplate;
        this.properties = properties;
    }

    public SlidingWindowResult recordAndCheck(String fingerprintHash) {
        return recordAndCheck(fingerprintHash, properties.getWindowSizeSeconds(), properties.getMaxReplayCount());
    }

    public SlidingWindowResult recordAndCheck(String fingerprintHash, int windowSizeSeconds, int maxReplayCount) {
        int overlapPercent = properties.getWindow().getOverlapPercent();
        String currentKey = "replay:window:cur:" + fingerprintHash;
        String previousKey = "replay:window:prev:" + fingerprintHash;
        long now = System.currentTimeMillis();

        DefaultRedisScript<List> script = new DefaultRedisScript<>(DUAL_WINDOW_SCRIPT, List.class);
        List<Long> result = redisTemplate.execute(
                script,
                List.of(currentKey, previousKey),
                String.valueOf(now),
                String.valueOf(windowSizeSeconds),
                fingerprintHash,
                String.valueOf(maxReplayCount),
                String.valueOf(overlapPercent)
        );

        if (result == null || result.size() < 7) {
            log.warn("Dual window script returned unexpected result for fingerprint: {}", fingerprintHash);
            return new SlidingWindowResult(1, false, now - windowSizeSeconds * 1000L, 1, 0, false);
        }

        long totalCount = result.get(0);
        boolean isReplay = result.get(1) == 1L;
        long windowStart = result.get(2);
        long currentCount = result.get(3);
        long prevCount = result.get(4);
        boolean isOverlap = result.get(5) == 1L;
        long epoch = result.get(6);

        log.debug("Dual window check: hash={}, total={}, current={}, prev={}, overlap={}, replay={}, epoch={}",
                fingerprintHash, totalCount, currentCount, prevCount, isOverlap, isReplay, epoch);

        return new SlidingWindowResult((int) totalCount, isReplay, windowStart,
                (int) currentCount, (int) prevCount, isOverlap);
    }

    public WindowStats getStats(String fingerprintHash) {
        int windowSizeSeconds = properties.getWindowSizeSeconds();
        long now = System.currentTimeMillis();
        long windowStart = now - windowSizeSeconds * 1000L;
        int halfWindow = Math.max(1, windowSizeSeconds / 2);
        long currentEpoch = now / (halfWindow * 1000L);

        String currentKey = "replay:window:cur:" + fingerprintHash + ":e:" + currentEpoch;
        String previousKey = "replay:window:prev:" + fingerprintHash + ":e:" + (currentEpoch - 1);

        Long currentCount = redisTemplate.opsForZSet().count(currentKey, windowStart, now);
        Long prevCount = redisTemplate.opsForZSet().count(previousKey, windowStart, now);

        int cur = currentCount != null ? currentCount.intValue() : 0;
        int prev = prevCount != null ? prevCount.intValue() : 0;

        return WindowStats.builder()
                .fingerprintHash(fingerprintHash)
                .windowStart(windowStart)
                .windowEnd(now)
                .requestCount(cur + prev)
                .currentWindowCount(cur)
                .previousWindowCount(prev)
                .overlapActive(prev > 0)
                .build();
    }

    public void clearWindow(String fingerprintHash) {
        var keys = redisTemplate.keys("replay:window:*:" + fingerprintHash + "*");
        if (keys != null && !keys.isEmpty()) {
            redisTemplate.delete(keys);
        }
        log.info("Cleared dual windows for fingerprint: {}", fingerprintHash);
    }

    public record SlidingWindowResult(
            int count,
            boolean isReplay,
            long windowStart,
            int currentWindowCount,
            int previousWindowCount,
            boolean overlapActive
    ) {}
}
