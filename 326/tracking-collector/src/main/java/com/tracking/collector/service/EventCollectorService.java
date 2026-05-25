package com.tracking.collector.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.tracking.collector.config.CollectorConfig;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.TrackEvent;
import com.tracking.common.util.EventValidator;
import com.tracking.common.util.IPUtil;
import com.tracking.common.util.IdGenerator;
import com.tracking.common.util.UserAgentUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;
import org.springframework.util.concurrent.ListenableFuture;
import org.springframework.util.concurrent.ListenableFutureCallback;

import javax.servlet.http.HttpServletRequest;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class EventCollectorService {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final CollectorConfig collectorConfig;

    @Value("${tracking.kafka.topic.raw-events}")
    private String rawEventsTopic;

    private final BlockingQueue<TrackEvent> eventQueue;
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

    public EventCollectorService(KafkaTemplate<String, String> kafkaTemplate, CollectorConfig collectorConfig) {
        this.kafkaTemplate = kafkaTemplate;
        this.collectorConfig = collectorConfig;
        this.eventQueue = new ArrayBlockingQueue<>(collectorConfig.getMaxQueueSize());

        startBatchSender();
    }

    private void startBatchSender() {
        scheduler.scheduleAtFixedRate(() -> {
            try {
                flushBatch();
            } catch (Exception e) {
                log.error("Error flushing event batch", e);
            }
        }, collectorConfig.getFlushIntervalMs(), collectorConfig.getFlushIntervalMs(), TimeUnit.MILLISECONDS);
    }

    private void flushBatch() {
        List<TrackEvent> batch = new ArrayList<>();
        eventQueue.drainTo(batch, collectorConfig.getBatchSize());
        if (!batch.isEmpty()) {
            sendBatchToKafka(batch);
        }
    }

    private void sendBatchToKafka(List<TrackEvent> batch) {
        for (TrackEvent event : batch) {
            sendToKafka(event);
        }
    }

    public EventValidator.ValidationResult collect(TrackEvent event, HttpServletRequest request) {
        EventValidator.ValidationResult result = EventValidator.validate(event);
        if (!result.isValid()) {
            log.warn("Event validation failed: {}", result.getErrors());
            return result;
        }

        if (!collectorConfig.isAppIdAllowed(event.getAppId())) {
            return EventValidator.ValidationResult.error("appId not allowed: " + event.getAppId());
        }

        enrichEvent(event, request);

        if (eventQueue.offer(event)) {
            if (eventQueue.size() >= collectorConfig.getBatchSize()) {
                flushBatch();
            }
        } else {
            log.warn("Event queue is full, dropping event: {}", event.getId());
        }

        return result;
    }

    public EventValidator.ValidationResult collectBatch(List<TrackEvent> events, HttpServletRequest request) {
        EventValidator.ValidationResult result = EventValidator.ValidationResult.ok();
        int successCount = 0;

        for (TrackEvent event : events) {
            EventValidator.ValidationResult singleResult = EventValidator.validate(event);
            if (!singleResult.isValid()) {
                singleResult.getErrors().forEach(result::addError);
                continue;
            }
            if (!collectorConfig.isAppIdAllowed(event.getAppId())) {
                result.addError("appId not allowed: " + event.getAppId());
                continue;
            }

            enrichEvent(event, request);

            if (eventQueue.offer(event)) {
                successCount++;
            } else {
                log.warn("Event queue is full, dropping event: {}", event.getId());
            }
        }

        if (successCount > 0 && eventQueue.size() >= collectorConfig.getBatchSize()) {
            flushBatch();
        }

        return result;
    }

    private void enrichEvent(TrackEvent event, HttpServletRequest request) {
        if (event.getId() == null) {
            event.setId(IdGenerator.generateEventId());
        }

        if (event.getReceiveTime() == null) {
            event.setReceiveTime(System.currentTimeMillis());
        }

        if (event.getSource() == null) {
            event.setSource(TrackingConstants.SOURCE_FRONTEND);
        }

        if (collectorConfig.isEnableIpParse() && request != null) {
            String clientIP = getClientIP(request);
            if (event.getIp() == null) {
                event.setIp(clientIP);
            }
        }

        if (collectorConfig.isEnableUserAgentParse() && request != null) {
            String userAgent = request.getHeader("User-Agent");
            if (event.getUserAgent() == null && userAgent != null) {
                event.setUserAgent(userAgent);
            }
            if (userAgent != null) {
                JSONObject uaInfo = UserAgentUtil.parse(userAgent);
                if (event.getOs() == null) {
                    event.setOs(uaInfo.getString("os"));
                }
                if (event.getOsVersion() == null) {
                    event.setOsVersion(uaInfo.getString("osVersion"));
                }
                if (event.getDeviceModel() == null) {
                    event.setDeviceModel(uaInfo.getString("device"));
                }
                if (event.getPlatform() == null) {
                    event.setPlatform(uaInfo.getBooleanValue("isMobile") ? "mobile" : "web");
                }
            }
        }

        if (event.getAnonymousId() == null && event.getDeviceId() != null) {
            event.setAnonymousId(IdGenerator.generateAnonymousId());
        }

        if (event.getSessionId() == null) {
            event.setSessionId(IdGenerator.generateSessionId());
        }
    }

    private String getClientIP(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_CLIENT_IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_X_FORWARDED_FOR");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        return IPUtil.extractIP(ip);
    }

    private void sendToKafka(TrackEvent event) {
        String message = JSON.toJSONString(event);
        String key = event.getUserId() != null ? event.getUserId() :
                (event.getAnonymousId() != null ? event.getAnonymousId() : event.getDeviceId());

        ListenableFuture<SendResult<String, String>> future = kafkaTemplate.send(rawEventsTopic, key, message);

        future.addCallback(new ListenableFutureCallback<SendResult<String, String>>() {
            @Override
            public void onSuccess(SendResult<String, String> result) {
                log.debug("Event sent to Kafka successfully: {}", event.getId());
            }

            @Override
            public void onFailure(Throwable ex) {
                log.error("Failed to send event to Kafka: {}, error: {}", event.getId(), ex.getMessage());
            }
        });
    }
}
