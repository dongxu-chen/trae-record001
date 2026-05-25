package com.tracking.sdk.java;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.IdGenerator;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import okhttp3.*;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.*;

@Slf4j
public class JavaTrackingSDK {

    private static final MediaType JSON_TYPE = MediaType.parse("application/json; charset=utf-8");

    private final String serverUrl;
    private final String appId;
    private final String appVersion;
    private final String channel;
    private final int batchSize;
    private final long flushIntervalMs;
    private final boolean debug;

    private final BlockingQueue<TrackEvent> eventQueue;
    private final ScheduledExecutorService scheduler;
    private final OkHttpClient httpClient;

    private final Map<String, String> commonProperties;

    @Builder
    public JavaTrackingSDK(String serverUrl, String appId, String appVersion, String channel,
                           int batchSize, long flushIntervalMs, boolean debug,
                           Map<String, String> commonProperties) {
        this.serverUrl = serverUrl != null ? serverUrl : "http://localhost:8080/tracking";
        this.appId = appId != null ? appId : "default_app";
        this.appVersion = appVersion != null ? appVersion : "1.0.0";
        this.channel = channel != null ? channel : "server";
        this.batchSize = batchSize > 0 ? batchSize : 50;
        this.flushIntervalMs = flushIntervalMs > 0 ? flushIntervalMs : 5000;
        this.debug = debug;
        this.commonProperties = commonProperties != null ? commonProperties : new HashMap<>();

        this.eventQueue = new LinkedBlockingQueue<>(10000);
        this.scheduler = Executors.newSingleThreadScheduledExecutor();
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(5, TimeUnit.SECONDS)
                .writeTimeout(5, TimeUnit.SECONDS)
                .build();

        startAutoFlush();
        log.info("Java Tracking SDK initialized, serverUrl: {}", this.serverUrl);
    }

    private void startAutoFlush() {
        scheduler.scheduleAtFixedRate(() -> {
            try {
                flush();
            } catch (Exception e) {
                log.error("Error flushing events", e);
            }
        }, flushIntervalMs, flushIntervalMs, TimeUnit.MILLISECONDS);
    }

    public void track(String eventName, Map<String, Object> properties) {
        track(eventName, properties, null, null);
    }

    public void track(String eventName, Map<String, Object> properties, String userId, String anonymousId) {
        TrackEvent event = TrackEvent.builder()
                .id(IdGenerator.generateEventId())
                .event(eventName)
                .timestamp(System.currentTimeMillis())
                .userId(userId)
                .anonymousId(anonymousId != null ? anonymousId : commonProperties.get("anonymousId"))
                .sessionId(commonProperties.get("sessionId"))
                .deviceId(commonProperties.get("deviceId"))
                .appId(appId)
                .appVersion(appVersion)
                .channel(channel)
                .platform("server")
                .source("backend")
                .properties(properties != null ? properties : new HashMap<>())
                .build();

        if (debug) {
            log.debug("Tracking event: {}", JSON.toJSONString(event));
        }

        if (!eventQueue.offer(event)) {
            log.warn("Event queue is full, dropping event: {}", eventName);
        }

        if (eventQueue.size() >= batchSize) {
            flush();
        }
    }

    public void trackUserAction(String userId, String action, Map<String, Object> properties) {
        if (properties == null) {
            properties = new HashMap<>();
        }
        properties.put("action", action);
        track(action, properties, userId, null);
    }

    public void trackPurchase(String userId, String orderId, double amount, Map<String, Object> extra) {
        Map<String, Object> properties = new HashMap<>();
        properties.put("order_id", orderId);
        properties.put("order_amount", amount);
        if (extra != null) {
            properties.putAll(extra);
        }
        track("purchase", properties, userId, null);
    }

    public void trackLogin(String userId, String loginType, Map<String, Object> extra) {
        Map<String, Object> properties = new HashMap<>();
        properties.put("login_type", loginType);
        if (extra != null) {
            properties.putAll(extra);
        }
        track("login", properties, userId, null);
    }

    public void flush() {
        List<TrackEvent> batch = new ArrayList<>();
        eventQueue.drainTo(batch, batchSize);

        if (batch.isEmpty()) {
            return;
        }

        try {
            String url;
            String json;
            if (batch.size() == 1) {
                url = serverUrl + "/v1/backend/track";
                json = JSON.toJSONString(batch.get(0));
            } else {
                url = serverUrl + "/v1/backend/track/batch";
                json = JSON.toJSONString(batch);
            }

            RequestBody body = RequestBody.create(json, JSON_TYPE);
            Request request = new Request.Builder()
                    .url(url)
                    .post(body)
                    .addHeader("Content-Type", "application/json")
                    .build();

            httpClient.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    log.error("Failed to send events to server, returning to queue", e);
                    eventQueue.addAll(batch);
                }

                @Override
                public void onResponse(Call call, Response response) throws IOException {
                    if (!response.isSuccessful()) {
                        log.warn("Server returned non-success status: {}", response.code());
                        eventQueue.addAll(batch);
                    } else if (debug) {
                        log.debug("Successfully sent {} events", batch.size());
                    }
                    response.close();
                }
            });
        } catch (Exception e) {
            log.error("Error sending events", e);
            eventQueue.addAll(batch);
        }
    }

    public void flushSync() {
        List<TrackEvent> batch = new ArrayList<>();
        eventQueue.drainTo(batch, batchSize);

        if (batch.isEmpty()) {
            return;
        }

        try {
            String url;
            String json;
            if (batch.size() == 1) {
                url = serverUrl + "/v1/backend/track";
                json = JSON.toJSONString(batch.get(0));
            } else {
                url = serverUrl + "/v1/backend/track/batch";
                json = JSON.toJSONString(batch);
            }

            RequestBody body = RequestBody.create(json, JSON_TYPE);
            Request request = new Request.Builder()
                    .url(url)
                    .post(body)
                    .addHeader("Content-Type", "application/json")
                    .build();

            try (Response response = httpClient.newCall(request).execute()) {
                if (!response.isSuccessful()) {
                    log.warn("Server returned non-success status: {}", response.code());
                    eventQueue.addAll(batch);
                }
            }
        } catch (Exception e) {
            log.error("Error sending events", e);
            eventQueue.addAll(batch);
        }
    }

    public void shutdown() {
        flushSync();
        scheduler.shutdown();
        try {
            if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                scheduler.shutdownNow();
            }
        } catch (InterruptedException e) {
            scheduler.shutdownNow();
        }
        httpClient.dispatcher().executorService().shutdown();
        httpClient.connectionPool().evictAll();
        log.info("Java Tracking SDK shutdown complete");
    }

    public void setCommonProperty(String key, String value) {
        commonProperties.put(key, value);
    }

    public void removeCommonProperty(String key) {
        commonProperties.remove(key);
    }

    public int getQueueSize() {
        return eventQueue.size();
    }

    @Data
    @Builder
    public static class SDKConfig {
        private String serverUrl;
        private String appId;
        private String appVersion;
        private String channel;
        private int batchSize;
        private long flushIntervalMs;
        private boolean debug;
        private Map<String, String> commonProperties;
    }

    public static JavaTrackingSDK createDefault() {
        return JavaTrackingSDK.builder().build();
    }

    public static JavaTrackingSDK create(SDKConfig config) {
        return new JavaTrackingSDK(
                config.getServerUrl(),
                config.getAppId(),
                config.getAppVersion(),
                config.getChannel(),
                config.getBatchSize(),
                config.getFlushIntervalMs(),
                config.isDebug(),
                config.getCommonProperties()
        );
    }
}
