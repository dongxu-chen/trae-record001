package com.pushcenter.service;

import com.pushcenter.enums.PushChannel;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.LongAdder;

@Slf4j
@Service
public class MessageStatisticsService {

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    private final Map<PushChannel, LongAdder> successCounters = new ConcurrentHashMap<>();
    private final Map<PushChannel, LongAdder> failureCounters = new ConcurrentHashMap<>();

    private static final String STATS_PREFIX = "push_center:stats:";
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    public MessageStatisticsService() {
        for (PushChannel channel : PushChannel.values()) {
            successCounters.put(channel, new LongAdder());
            failureCounters.put(channel, new LongAdder());
        }
    }

    public void recordSuccess(PushChannel channel) {
        successCounters.get(channel).increment();
        persistStat(channel, "success", 1);
    }

    public void recordFailure(PushChannel channel) {
        failureCounters.get(channel).increment();
        persistStat(channel, "failure", 1);
    }

    private void persistStat(PushChannel channel, String type, long count) {
        String date = LocalDate.now().format(DATE_FORMATTER);
        String key = STATS_PREFIX + date + ":" + channel.getCode() + ":" + type;
        redisTemplate.opsForValue().increment(key, count);
    }

    public long getSuccessCount(PushChannel channel) {
        return successCounters.get(channel).sum();
    }

    public long getFailureCount(PushChannel channel) {
        return failureCounters.get(channel).sum();
    }

    public long getTotalCount(PushChannel channel) {
        return getSuccessCount(channel) + getFailureCount(channel);
    }

    public Map<String, Object> getChannelStats(PushChannel channel) {
        Map<String, Object> stats = new HashMap<>();
        stats.put("channel", channel.getCode());
        stats.put("success", getSuccessCount(channel));
        stats.put("failure", getFailureCount(channel));
        stats.put("total", getTotalCount(channel));
        long total = getTotalCount(channel);
        stats.put("successRate", total > 0 ? (getSuccessCount(channel) * 100.0 / total) : 0);
        return stats;
    }

    public Map<String, Object> getAllStats() {
        Map<String, Object> allStats = new HashMap<>();
        long totalSuccess = 0;
        long totalFailure = 0;

        for (PushChannel channel : PushChannel.values()) {
            allStats.put(channel.getCode(), getChannelStats(channel));
            totalSuccess += getSuccessCount(channel);
            totalFailure += getFailureCount(channel);
        }

        allStats.put("totalSuccess", totalSuccess);
        allStats.put("totalFailure", totalFailure);
        allStats.put("total", totalSuccess + totalFailure);
        allStats.put("overallSuccessRate", (totalSuccess + totalFailure) > 0
                ? (totalSuccess * 100.0 / (totalSuccess + totalFailure)) : 0);

        return allStats;
    }

    public void resetCounters() {
        for (PushChannel channel : PushChannel.values()) {
            successCounters.get(channel).reset();
            failureCounters.get(channel).reset();
        }
    }
}
