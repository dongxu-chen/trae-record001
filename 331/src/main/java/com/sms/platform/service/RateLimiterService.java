package com.sms.platform.service;

import com.sms.platform.entity.SmsChannelConfig;
import com.sms.platform.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class RateLimiterService {

    @Resource
    private RedisUtil redisUtil;

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    @Resource
    private ChannelManagerService channelManagerService;

    @Value("${sms.rate-limit.enabled:true}")
    private boolean rateLimitEnabled;

    private static final String TOKEN_BUCKET_KEY_PREFIX = "sms:token:bucket:";
    private static final String TOKENS_FIELD = "tokens";
    private static final String LAST_REFRESH_FIELD = "last_refresh";

    private static final RedisScript<Long> TOKEN_BUCKET_SCRIPT = new DefaultRedisScript<>(
            "local key = KEYS[1] " +
            "local capacity = tonumber(ARGV[1]) " +
            "local rate = tonumber(ARGV[2]) " +
            "local now = tonumber(ARGV[3]) " +
            "local requested = tonumber(ARGV[4]) " +
            "local fill_time = capacity / rate " +
            "local ttl = math.floor(fill_time * 2) " +
            "local last_tokens = tonumber(redis.call('hget', key, '" + TOKENS_FIELD + "') or -1) " +
            "local last_refresh = tonumber(redis.call('hget', key, '" + LAST_REFRESH_FIELD + "') or 0) " +
            "local delta = math.max(0, now - last_refresh) " +
            "local filled_tokens = math.min(capacity, last_tokens + delta * rate / 1000) " +
            "local allowed = filled_tokens >= requested " +
            "local new_tokens = filled_tokens " +
            "if allowed then " +
            "    new_tokens = filled_tokens - requested " +
            "end " +
            "redis.call('hset', key, '" + TOKENS_FIELD + "', new_tokens) " +
            "redis.call('hset', key, '" + LAST_REFRESH_FIELD + "', now) " +
            "redis.call('expire', key, ttl) " +
            "if allowed then " +
            "    return 1 " +
            "else " +
            "    return 0 " +
            "end",
            Long.class
    );

    public boolean tryAcquire(Integer channelCode) {
        return tryAcquire(channelCode, 1);
    }

    public boolean tryAcquire(Integer channelCode, int requestedTokens) {
        if (!rateLimitEnabled) {
            return true;
        }

        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);
        if (config == null) {
            log.warn("通道配置不存在，跳过限流检查: {}", channelCode);
            return true;
        }

        Integer capacity = config.getTokenBucketCapacity();
        Integer rate = config.getTokenBucketRate();

        if (capacity == null || capacity <= 0) {
            capacity = 1000;
        }
        if (rate == null || rate <= 0) {
            rate = 100;
        }

        return tryAcquireTokenBucket(channelCode, capacity, rate, requestedTokens);
    }

    private boolean tryAcquireTokenBucket(Integer channelCode, int capacity, int rate, int requestedTokens) {
        String key = TOKEN_BUCKET_KEY_PREFIX + channelCode;
        long now = System.currentTimeMillis();

        try {
            List<String> keys = Collections.singletonList(key);
            Long result = redisTemplate.execute(
                    TOKEN_BUCKET_SCRIPT,
                    keys,
                    String.valueOf(capacity),
                    String.valueOf(rate),
                    String.valueOf(now),
                    String.valueOf(requestedTokens)
            );

            boolean allowed = result != null && result == 1;

            if (!allowed) {
                log.warn("通道 {} 触发令牌桶限流, capacity={}, rate={}/秒, requested={}",
                        channelCode, capacity, rate, requestedTokens);
            }

            return allowed;
        } catch (Exception e) {
            log.error("令牌桶限流检查异常, channelCode: {}", channelCode, e);
            return tryAcquireFallback(channelCode, capacity, rate, requestedTokens);
        }
    }

    private boolean tryAcquireFallback(Integer channelCode, int capacity, int rate, int requestedTokens) {
        String key = TOKEN_BUCKET_KEY_PREFIX + channelCode;
        long now = System.currentTimeMillis();

        try {
            Map<Object, Object> bucket = redisUtil.hGetAll(key);
            double currentTokens;
            long lastRefresh;

            if (bucket.isEmpty()) {
                currentTokens = capacity;
                lastRefresh = now;
            } else {
                Object tokensObj = bucket.get(TOKENS_FIELD);
                Object refreshObj = bucket.get(LAST_REFRESH_FIELD);
                currentTokens = tokensObj != null ? ((Number) tokensObj).doubleValue() : capacity;
                lastRefresh = refreshObj != null ? ((Number) refreshObj).longValue() : now;
            }

            long delta = Math.max(0, now - lastRefresh);
            double newTokens = Math.min(capacity, currentTokens + delta * rate / 1000.0);

            if (newTokens >= requestedTokens) {
                Map<String, Object> updateMap = new HashMap<>();
                updateMap.put(TOKENS_FIELD, newTokens - requestedTokens);
                updateMap.put(LAST_REFRESH_FIELD, now);
                redisUtil.hSetAll(key, updateMap);

                long ttl = (long) (capacity * 2000.0 / rate);
                redisUtil.expire(key, ttl, TimeUnit.MILLISECONDS);

                return true;
            } else {
                Map<String, Object> updateMap = new HashMap<>();
                updateMap.put(TOKENS_FIELD, newTokens);
                updateMap.put(LAST_REFRESH_FIELD, now);
                redisUtil.hSetAll(key, updateMap);

                long ttl = (long) (capacity * 2000.0 / rate);
                redisUtil.expire(key, ttl, TimeUnit.MILLISECONDS);

                log.warn("通道 {} 触发令牌桶限流(降级), 当前令牌: {}, 需要: {}", channelCode, newTokens, requestedTokens);
                return false;
            }
        } catch (Exception e) {
            log.error("令牌桶降级限流检查异常, channelCode: {}", channelCode, e);
            return true;
        }
    }

    public long getAvailableTokens(Integer channelCode) {
        String key = TOKEN_BUCKET_KEY_PREFIX + channelCode;
        try {
            Object tokens = redisUtil.hGet(key, TOKENS_FIELD);
            return tokens != null ? ((Number) tokens).longValue() : 0;
        } catch (Exception e) {
            log.error("获取可用令牌数异常", e);
            return 0;
        }
    }

    public Map<String, Object> getTokenBucketStatus(Integer channelCode) {
        Map<String, Object> status = new HashMap<>();
        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);

        if (config != null) {
            status.put("channelCode", channelCode);
            status.put("capacity", config.getTokenBucketCapacity());
            status.put("rate", config.getTokenBucketRate());
            status.put("availableTokens", getAvailableTokens(channelCode));
            status.put("maxSendPerSecond", config.getMaxSendPerSecond());
            status.put("maxSendPerMinute", config.getMaxSendPerMinute());
            status.put("maxSendPerHour", config.getMaxSendPerHour());
        }

        return status;
    }

    public void resetLimit(Integer channelCode) {
        String key = TOKEN_BUCKET_KEY_PREFIX + channelCode;
        try {
            redisUtil.delete(key);
            log.info("通道 {} 令牌桶已重置", channelCode);
        } catch (Exception e) {
            log.error("重置令牌桶异常", e);
        }
    }

    public void refillBucket(Integer channelCode) {
        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);
        if (config == null || config.getTokenBucketCapacity() == null) {
            return;
        }

        String key = TOKEN_BUCKET_KEY_PREFIX + channelCode;
        try {
            Map<String, Object> updateMap = new HashMap<>();
            updateMap.put(TOKENS_FIELD, config.getTokenBucketCapacity());
            updateMap.put(LAST_REFRESH_FIELD, System.currentTimeMillis());
            redisUtil.hSetAll(key, updateMap);
            log.info("通道 {} 令牌桶已补满, 容量: {}", channelCode, config.getTokenBucketCapacity());
        } catch (Exception e) {
            log.error("补满令牌桶异常", e);
        }
    }
}
