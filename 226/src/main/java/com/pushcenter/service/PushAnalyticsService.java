package com.pushcenter.service;

import com.pushcenter.enums.PushChannel;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class PushAnalyticsService {

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    private static final String ANALYTICS_PREFIX = "push_center:analytics:";
    private static final String AB_TEST_PREFIX = "push_center:ab_test:";
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    public void recordSent(PushChannel channel, String messageId, String userId, String templateCode) {
        String date = LocalDate.now().format(DATE_FORMATTER);
        recordMetric(channel, date, "sent", 1);
        recordMessageEvent(messageId, "sent", System.currentTimeMillis());
    }

    public void recordArrival(PushChannel channel, String messageId) {
        String date = LocalDate.now().format(DATE_FORMATTER);
        recordMetric(channel, date, "arrived", 1);
        recordMessageEvent(messageId, "arrived", System.currentTimeMillis());
    }

    public void recordClick(String messageId) {
        Map<String, Object> metadata = getMessageMetadata(messageId);
        if (metadata != null && metadata.get("channel") != null) {
            PushChannel channel = PushChannel.fromCode((String) metadata.get("channel"));
            if (channel != null) {
                String date = LocalDate.now().format(DATE_FORMATTER);
                recordMetric(channel, date, "clicked", 1);
            }
        }
        recordMessageEvent(messageId, "clicked", System.currentTimeMillis());
    }

    public void recordConversion(String messageId, String conversionType) {
        Map<String, Object> metadata = getMessageMetadata(messageId);
        if (metadata != null && metadata.get("channel") != null) {
            PushChannel channel = PushChannel.fromCode((String) metadata.get("channel"));
            if (channel != null) {
                String date = LocalDate.now().format(DATE_FORMATTER);
                recordMetric(channel, date, "converted", 1);
                recordMetric(channel, date, "conversion_" + conversionType, 1);
            }
        }
        recordMessageEvent(messageId, "converted", System.currentTimeMillis());
    }

    private void recordMetric(PushChannel channel, String date, String metric, long count) {
        String key = ANALYTICS_PREFIX + date + ":" + channel.getCode() + ":" + metric;
        redisTemplate.opsForValue().increment(key, count);
        redisTemplate.expire(key, 90, TimeUnit.DAYS);
    }

    private void recordMessageEvent(String messageId, String event, long timestamp) {
        String key = ANALYTICS_PREFIX + "message:" + messageId + ":events";
        redisTemplate.opsForHash().put(key, event, timestamp);
        redisTemplate.expire(key, 90, TimeUnit.DAYS);
    }

    public void recordMessageMetadata(String messageId, PushChannel channel, String templateCode, String userId) {
        String key = ANALYTICS_PREFIX + "message:" + messageId + ":meta";
        Map<String, Object> meta = new HashMap<>();
        meta.put("messageId", messageId);
        meta.put("channel", channel.getCode());
        meta.put("templateCode", templateCode);
        meta.put("userId", userId);
        meta.put("timestamp", System.currentTimeMillis());
        redisTemplate.opsForHash().putAll(key, meta);
        redisTemplate.expire(key, 90, TimeUnit.DAYS);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getMessageMetadata(String messageId) {
        String key = ANALYTICS_PREFIX + "message:" + messageId + ":meta";
        Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
        Map<String, Object> result = new HashMap<>();
        for (Map.Entry<Object, Object> entry : entries.entrySet()) {
            result.put((String) entry.getKey(), entry.getValue());
        }
        return result.isEmpty() ? null : result;
    }

    public Map<String, Object> getChannelAnalytics(PushChannel channel, int days) {
        Map<String, Object> analytics = new HashMap<>();
        long totalSent = 0;
        long totalArrived = 0;
        long totalClicked = 0;
        long totalConverted = 0;

        LocalDate today = LocalDate.now();
        for (int i = 0; i < days; i++) {
            String date = today.minusDays(i).format(DATE_FORMATTER);
            totalSent += getMetric(channel, date, "sent");
            totalArrived += getMetric(channel, date, "arrived");
            totalClicked += getMetric(channel, date, "clicked");
            totalConverted += getMetric(channel, date, "converted");
        }

        analytics.put("channel", channel.getCode());
        analytics.put("days", days);
        analytics.put("sent", totalSent);
        analytics.put("arrived", totalArrived);
        analytics.put("clicked", totalClicked);
        analytics.put("converted", totalConverted);
        analytics.put("arrivalRate", totalSent > 0 ? (totalArrived * 100.0 / totalSent) : 0);
        analytics.put("clickRate", totalArrived > 0 ? (totalClicked * 100.0 / totalArrived) : 0);
        analytics.put("conversionRate", totalClicked > 0 ? (totalConverted * 100.0 / totalClicked) : 0);
        analytics.put("overallConversionRate", totalSent > 0 ? (totalConverted * 100.0 / totalSent) : 0);

        return analytics;
    }

    public Map<String, Object> getAllChannelAnalytics(int days) {
        Map<String, Object> allAnalytics = new HashMap<>();
        for (PushChannel channel : PushChannel.values()) {
            allAnalytics.put(channel.getCode(), getChannelAnalytics(channel, days));
        }
        return allAnalytics;
    }

    private long getMetric(PushChannel channel, String date, String metric) {
        String key = ANALYTICS_PREFIX + date + ":" + channel.getCode() + ":" + metric;
        Object value = redisTemplate.opsForValue().get(key);
        return value != null ? ((Integer) value).longValue() : 0;
    }

    public String createABTest(String testName, List<String> variantNames, List<String> templateCodes) {
        String testId = UUID.randomUUID().toString();
        String key = AB_TEST_PREFIX + testId;

        Map<String, Object> testConfig = new HashMap<>();
        testConfig.put("testId", testId);
        testConfig.put("testName", testName);
        testConfig.put("status", "running");
        testConfig.put("createdAt", System.currentTimeMillis());

        List<Map<String, Object>> variants = new ArrayList<>();
        for (int i = 0; i < variantNames.size(); i++) {
            Map<String, Object> variant = new HashMap<>();
            variant.put("name", variantNames.get(i));
            variant.put("templateCode", templateCodes.get(i));
            variant.put("assigned", 0);
            variant.put("sent", 0);
            variant.put("arrived", 0);
            variant.put("clicked", 0);
            variant.put("converted", 0);
            variants.add(variant);
        }

        redisTemplate.opsForHash().put(key, "config", testConfig);
        redisTemplate.opsForHash().put(key, "variants", variants);
        redisTemplate.expire(key, 90, TimeUnit.DAYS);

        log.info("A/B Test created: {} ({})", testName, testId);
        return testId;
    }

    @SuppressWarnings("unchecked")
    public String assignABTestVariant(String testId, String userId) {
        String key = AB_TEST_PREFIX + testId;
        String assignmentKey = AB_TEST_PREFIX + testId + ":assignments";

        Object existingAssignment = redisTemplate.opsForHash().get(assignmentKey, userId);
        if (existingAssignment != null) {
            return (String) existingAssignment;
        }

        List<Map<String, Object>> variants = (List<Map<String, Object>>) redisTemplate.opsForHash().get(key, "variants");
        if (variants == null || variants.isEmpty()) {
            return null;
        }

        int variantIndex = Math.abs(userId.hashCode()) % variants.size();
        Map<String, Object> variant = variants.get(variantIndex);
        String variantName = (String) variant.get("name");

        redisTemplate.opsForHash().put(assignmentKey, userId, variantName);
        variant.put("assigned", ((Integer) variant.get("assigned")) + 1);
        redisTemplate.opsForHash().put(key, "variants", variants);

        return variantName;
    }

    public Map<String, Object> getABTestResults(String testId) {
        String key = AB_TEST_PREFIX + testId;
        Map<String, Object> result = new HashMap<>();

        Object config = redisTemplate.opsForHash().get(key, "config");
        Object variants = redisTemplate.opsForHash().get(key, "variants");

        result.put("config", config);
        result.put("variants", calculateVariantStats((List<Map<String, Object>>) variants));

        return result;
    }

    private List<Map<String, Object>> calculateVariantStats(List<Map<String, Object>> variants) {
        if (variants == null) {
            return Collections.emptyList();
        }

        for (Map<String, Object> variant : variants) {
            int sent = (Integer) variant.getOrDefault("sent", 0);
            int arrived = (Integer) variant.getOrDefault("arrived", 0);
            int clicked = (Integer) variant.getOrDefault("clicked", 0);
            int converted = (Integer) variant.getOrDefault("converted", 0);

            variant.put("arrivalRate", sent > 0 ? (arrived * 100.0 / sent) : 0);
            variant.put("clickRate", arrived > 0 ? (clicked * 100.0 / arrived) : 0);
            variant.put("conversionRate", clicked > 0 ? (converted * 100.0 / clicked) : 0);
        }

        return variants;
    }

    public void stopABTest(String testId, String winner) {
        String key = AB_TEST_PREFIX + testId;
        @SuppressWarnings("unchecked")
        Map<String, Object> config = (Map<String, Object>) redisTemplate.opsForHash().get(key, "config");
        if (config != null) {
            config.put("status", "completed");
            config.put("winner", winner);
            config.put("completedAt", System.currentTimeMillis());
            redisTemplate.opsForHash().put(key, "config", config);
        }
        log.info("A/B Test stopped: {}, winner: {}", testId, winner);
    }

    public Map<String, Object> getEventTimeline(String messageId) {
        String key = ANALYTICS_PREFIX + "message:" + messageId + ":events";
        Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
        Map<String, Object> timeline = new HashMap<>();
        for (Map.Entry<Object, Object> entry : entries.entrySet()) {
            timeline.put((String) entry.getKey(), entry.getValue());
        }
        return timeline;
    }
}
