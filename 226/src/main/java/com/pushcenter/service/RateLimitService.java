package com.pushcenter.service;

import com.pushcenter.enums.PushChannel;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class RateLimitService {

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    @Value("${pushcenter.rate-limit.sms.rate:100}")
    private long smsRate;

    @Value("${pushcenter.rate-limit.sms.capacity:1000}")
    private long smsCapacity;

    @Value("${pushcenter.rate-limit.email.rate:500}")
    private long emailRate;

    @Value("${pushcenter.rate-limit.email.capacity:5000}")
    private long emailCapacity;

    @Value("${pushcenter.rate-limit.dingtalk.rate:200}")
    private long dingtalkRate;

    @Value("${pushcenter.rate-limit.dingtalk.capacity:2000}")
    private long dingtalkCapacity;

    @Value("${pushcenter.rate-limit.wechat-work.rate:200}")
    private long wechatWorkRate;

    @Value("${pushcenter.rate-limit.wechat-work.capacity:2000}")
    private long wechatWorkCapacity;

    @Value("${pushcenter.rate-limit.app-push.rate:1000}")
    private long appPushRate;

    @Value("${pushcenter.rate-limit.app-push.capacity:10000}")
    private long appPushCapacity;

    private final Map<PushChannel, long[]> channelConfig = new ConcurrentHashMap<>();

    private static final String RATE_LIMIT_PREFIX = "push_center:rate_limit:";

    private static final String TOKEN_BUCKET_SCRIPT =
            "local tokens_key = KEYS[1] " +
            "local timestamp_key = KEYS[2] " +
            "local rate = tonumber(ARGV[1]) " +
            "local capacity = tonumber(ARGV[2]) " +
            "local now = tonumber(ARGV[3]) " +
            "local requested = tonumber(ARGV[4]) " +
            "local fill_time = capacity/rate " +
            "local ttl = math.floor(fill_time*2) " +
            "local last_tokens = tonumber(redis.call('get', tokens_key)) " +
            "if last_tokens == nil then " +
            "    last_tokens = capacity " +
            "end " +
            "local last_refreshed = tonumber(redis.call('get', timestamp_key)) " +
            "if last_refreshed == nil then " +
            "    last_refreshed = 0 " +
            "end " +
            "local delta = math.max(0, now-last_refreshed) " +
            "local filled_tokens = math.min(capacity, last_tokens+(delta*rate/1000)) " +
            "local allowed = filled_tokens >= requested " +
            "local new_tokens = filled_tokens " +
            "if allowed then " +
            "    new_tokens = filled_tokens - requested " +
            "end " +
            "redis.call('setex', tokens_key, ttl, new_tokens) " +
            "redis.call('setex', timestamp_key, ttl, now) " +
            "return allowed";

    private static final String GET_TOKENS_SCRIPT =
            "local tokens_key = KEYS[1] " +
            "local timestamp_key = KEYS[2] " +
            "local rate = tonumber(ARGV[1]) " +
            "local capacity = tonumber(ARGV[2]) " +
            "local now = tonumber(ARGV[3]) " +
            "local last_tokens = tonumber(redis.call('get', tokens_key)) " +
            "if last_tokens == nil then " +
            "    last_tokens = capacity " +
            "end " +
            "local last_refreshed = tonumber(redis.call('get', timestamp_key)) " +
            "if last_refreshed == nil then " +
            "    last_refreshed = 0 " +
            "end " +
            "local delta = math.max(0, now-last_refreshed) " +
            "local filled_tokens = math.min(capacity, last_tokens+(delta*rate/1000)) " +
            "return filled_tokens";

    @PostConstruct
    public void init() {
        channelConfig.put(PushChannel.SMS, new long[]{smsRate, smsCapacity});
        channelConfig.put(PushChannel.EMAIL, new long[]{emailRate, emailCapacity});
        channelConfig.put(PushChannel.DINGTALK, new long[]{dingtalkRate, dingtalkCapacity});
        channelConfig.put(PushChannel.WECHAT_WORK, new long[]{wechatWorkRate, wechatWorkCapacity});
        channelConfig.put(PushChannel.APP_PUSH, new long[]{appPushRate, appPushCapacity});

        log.info("RateLimitService initialized with Redis token bucket (multi-instance shared quota)");
        for (PushChannel channel : PushChannel.values()) {
            long[] config = channelConfig.get(channel);
            log.info("  {}: rate={}/s, capacity={}", channel.getName(), config[0], config[1]);
        }
    }

    public boolean tryAcquire(PushChannel channel) {
        return tryAcquire(channel, 1);
    }

    public boolean tryAcquire(PushChannel channel, int permits) {
        String tokensKey = RATE_LIMIT_PREFIX + channel.getCode() + ":tokens";
        String timestampKey = RATE_LIMIT_PREFIX + channel.getCode() + ":timestamp";

        long[] config = channelConfig.get(channel);
        long rate = config[0];
        long capacity = config[1];
        long now = System.currentTimeMillis();

        RedisScript<Boolean> script = new DefaultRedisScript<>(TOKEN_BUCKET_SCRIPT, Boolean.class);

        try {
            Boolean result = redisTemplate.execute(
                    script,
                    Arrays.asList(tokensKey, timestampKey),
                    rate,
                    capacity,
                    now,
                    permits
            );
            return Boolean.TRUE.equals(result);
        } catch (Exception e) {
            log.error("Rate limit check failed for channel: {}", channel, e);
            return true;
        }
    }

    public long getAvailableTokens(PushChannel channel) {
        String tokensKey = RATE_LIMIT_PREFIX + channel.getCode() + ":tokens";
        String timestampKey = RATE_LIMIT_PREFIX + channel.getCode() + ":timestamp";

        long[] config = channelConfig.get(channel);
        long rate = config[0];
        long capacity = config[1];
        long now = System.currentTimeMillis();

        RedisScript<Long> script = new DefaultRedisScript<>(GET_TOKENS_SCRIPT, Long.class);

        try {
            Long result = redisTemplate.execute(
                    script,
                    Arrays.asList(tokensKey, timestampKey),
                    rate,
                    capacity,
                    now
            );
            return result != null ? result : 0;
        } catch (Exception e) {
            log.error("Get available tokens failed for channel: {}", channel, e);
            return 0;
        }
    }

    public Map<String, Object> getChannelRateLimitInfo(PushChannel channel) {
        long[] config = channelConfig.get(channel);
        Map<String, Object> info = new HashMap<>();
        info.put("channel", channel.getCode());
        info.put("ratePerSecond", config[0]);
        info.put("bucketCapacity", config[1]);
        info.put("availableTokens", getAvailableTokens(channel));
        return info;
    }

    public Map<String, Object> getAllRateLimitInfo() {
        Map<String, Object> allInfo = new HashMap<>();
        for (PushChannel channel : PushChannel.values()) {
            allInfo.put(channel.getCode(), getChannelRateLimitInfo(channel));
        }
        return allInfo;
    }

    public void resetLimit(PushChannel channel) {
        String tokensKey = RATE_LIMIT_PREFIX + channel.getCode() + ":tokens";
        String timestampKey = RATE_LIMIT_PREFIX + channel.getCode() + ":timestamp";
        redisTemplate.delete(Arrays.asList(tokensKey, timestampKey));
        log.info("Rate limit reset for channel: {}", channel);
    }

    public void updateRateLimit(PushChannel channel, long rate, long capacity) {
        channelConfig.put(channel, new long[]{rate, capacity});
        resetLimit(channel);
        log.info("Rate limit updated for channel: {} rate={}/s capacity={}", channel, rate, capacity);
    }
}
