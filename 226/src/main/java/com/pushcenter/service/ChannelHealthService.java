package com.pushcenter.service;

import com.pushcenter.enums.PushChannel;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class ChannelHealthService {

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    @Value("${pushcenter.health.window-minutes: 10}")
    private int windowMinutes;

    @Value("${pushcenter.health.degrade-threshold: 0.7}")
    private double degradeThreshold;

    @Value("${pushcenter.health.recover-threshold: 0.9}")
    private double recoverThreshold;

    private static final String HEALTH_METRICS_PREFIX = "push_center:health_metrics:";
    private static final String CHANNEL_STATUS_KEY = "push_center:channel_status";

    private final Map<PushChannel, Boolean> degradedChannels = new ConcurrentHashMap<>();
    private final Map<PushChannel, List<PushChannel>> fallbackChains = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        initFallbackChains();
        loadChannelStatus();
        log.info("ChannelHealthService initialized, degradeThreshold={}, recoverThreshold={}",
                degradeThreshold, recoverThreshold);
    }

    private void initFallbackChains() {
        fallbackChains.put(PushChannel.SMS, Arrays.asList(PushChannel.APP_PUSH, PushChannel.EMAIL));
        fallbackChains.put(PushChannel.EMAIL, Arrays.asList(PushChannel.APP_PUSH, PushChannel.SMS));
        fallbackChains.put(PushChannel.APP_PUSH, Arrays.asList(PushChannel.SMS, PushChannel.EMAIL));
        fallbackChains.put(PushChannel.DINGTALK, Arrays.asList(PushChannel.WECHAT_WORK, PushChannel.SMS));
        fallbackChains.put(PushChannel.WECHAT_WORK, Arrays.asList(PushChannel.DINGTALK, PushChannel.SMS));
    }

    private void loadChannelStatus() {
        Map<Object, Object> statusMap = redisTemplate.opsForHash().entries(CHANNEL_STATUS_KEY);
        for (Map.Entry<Object, Object> entry : statusMap.entrySet()) {
            PushChannel channel = PushChannel.fromCode((String) entry.getKey());
            if (channel != null) {
                degradedChannels.put(channel, (Boolean) entry.getValue());
            }
        }
    }

    public void recordSuccess(PushChannel channel) {
        recordMetric(channel, "success", 1);
    }

    public void recordFailure(PushChannel channel) {
        recordMetric(channel, "failure", 1);
    }

    private void recordMetric(PushChannel channel, String type, long count) {
        long windowStart = System.currentTimeMillis() / 60000 * 60000;
        String key = HEALTH_METRICS_PREFIX + channel.getCode() + ":" + windowStart;
        redisTemplate.opsForHash().increment(key, type, count);
        redisTemplate.expire(key, windowMinutes + 5, TimeUnit.MINUTES);
    }

    public double getSuccessRate(PushChannel channel) {
        long totalSuccess = 0;
        long totalFailure = 0;

        long now = System.currentTimeMillis();
        long windowStart = now - (windowMinutes * 60000L);

        for (int i = 0; i <= windowMinutes; i++) {
            long timeBucket = (windowStart + i * 60000L) / 60000 * 60000;
            String key = HEALTH_METRICS_PREFIX + channel.getCode() + ":" + timeBucket;

            Object success = redisTemplate.opsForHash().get(key, "success");
            Object failure = redisTemplate.opsForHash().get(key, "failure");

            if (success != null) {
                totalSuccess += ((Integer) success).longValue();
            }
            if (failure != null) {
                totalFailure += ((Integer) failure).longValue();
            }
        }

        long total = totalSuccess + totalFailure;
        if (total == 0) {
            return 1.0;
        }
        return (double) totalSuccess / total;
    }

    public double getHealthScore(PushChannel channel) {
        double successRate = getSuccessRate(channel);
        boolean isDegraded = isDegraded(channel);

        if (isDegraded && successRate >= recoverThreshold) {
            recoverChannel(channel);
            log.info("Channel {} recovered, success rate: {}", channel.getName(), successRate);
        } else if (!isDegraded && successRate < degradeThreshold) {
            degradeChannel(channel);
            log.warn("Channel {} degraded, success rate: {}", channel.getName(), successRate);
        }

        return successRate;
    }

    public void degradeChannel(PushChannel channel) {
        degradedChannels.put(channel, true);
        redisTemplate.opsForHash().put(CHANNEL_STATUS_KEY, channel.getCode(), true);
        log.warn("Channel {} marked as DEGRADED", channel.getName());
    }

    public void recoverChannel(PushChannel channel) {
        degradedChannels.put(channel, false);
        redisTemplate.opsForHash().put(CHANNEL_STATUS_KEY, channel.getCode(), false);
        log.info("Channel {} recovered from DEGRADED", channel.getName());
    }

    public boolean isDegraded(PushChannel channel) {
        return degradedChannels.getOrDefault(channel, false);
    }

    public PushChannel getFallbackChannel(PushChannel degradedChannel, Set<PushChannel> supportedChannels) {
        List<PushChannel> fallbacks = fallbackChains.get(degradedChannel);
        if (fallbacks == null) {
            return null;
        }

        for (PushChannel fallback : fallbacks) {
            if (supportedChannels.contains(fallback) && !isDegraded(fallback)) {
                log.info("Using fallback channel {} for degraded channel {}", fallback, degradedChannel);
                return fallback;
            }
        }

        return null;
    }

    public Map<String, Object> getChannelHealthInfo(PushChannel channel) {
        Map<String, Object> info = new HashMap<>();
        info.put("channel", channel.getCode());
        info.put("successRate", getSuccessRate(channel));
        info.put("healthScore", getHealthScore(channel));
        info.put("isDegraded", isDegraded(channel));
        info.put("fallbackChain", fallbackChains.get(channel));
        return info;
    }

    public Map<String, Object> getAllHealthInfo() {
        Map<String, Object> allInfo = new HashMap<>();
        for (PushChannel channel : PushChannel.values()) {
            allInfo.put(channel.getCode(), getChannelHealthInfo(channel));
        }
        return allInfo;
    }

    @Scheduled(fixedDelay = 60000)
    public void healthCheck() {
        log.debug("Running periodic channel health check");
        for (PushChannel channel : PushChannel.values()) {
            getHealthScore(channel);
        }
    }

    public void forceRecover(PushChannel channel) {
        recoverChannel(channel);
        log.info("Channel {} forcefully recovered", channel.getName());
    }

    public void forceDegrade(PushChannel channel) {
        degradeChannel(channel);
        log.info("Channel {} forcefully degraded", channel.getName());
    }
}
