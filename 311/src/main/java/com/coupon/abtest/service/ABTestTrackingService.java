package com.coupon.abtest.service;

import com.alibaba.fastjson2.JSON;
import com.coupon.clickhouse.repository.ABTestEventRepository;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
public class ABTestTrackingService {

    @Value("${spring.application.name:coupon-system}")
    private String applicationName;

    private final ABTestEventRepository eventRepository;

    public ABTestTrackingService(ABTestEventRepository eventRepository) {
        this.eventRepository = eventRepository;
    }

    public void trackExposure(String userId, String experimentId, String groupId, String scene) {
        TrackingEvent event = TrackingEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .eventType("exposure")
                .userId(userId)
                .experimentId(experimentId)
                .groupId(groupId)
                .scene(scene)
                .timestamp(LocalDateTime.now())
                .source(applicationName)
                .build();
        sendEvent(event);
    }

    public void trackConversion(String userId, String experimentId, String groupId,
                                String action, Map<String, Object> properties) {
        TrackingEvent event = TrackingEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .eventType("conversion")
                .userId(userId)
                .experimentId(experimentId)
                .groupId(groupId)
                .action(action)
                .timestamp(LocalDateTime.now())
                .source(applicationName)
                .properties(properties != null ? properties : new HashMap<>())
                .build();
        sendEvent(event);
    }

    public void trackCouponIssue(String userId, String experimentId, String groupId,
                                 String couponId, String scene, int rlActionIndex) {
        Map<String, Object> properties = new HashMap<>();
        properties.put("coupon_id", couponId);
        properties.put("rl_action_index", rlActionIndex);
        properties.put("scene", scene);

        TrackingEvent event = TrackingEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .eventType("coupon_issue")
                .userId(userId)
                .experimentId(experimentId)
                .groupId(groupId)
                .action("issue")
                .timestamp(LocalDateTime.now())
                .source(applicationName)
                .properties(properties)
                .build();
        sendEvent(event);
    }

    public void trackCouponUse(String userId, String experimentId, String groupId,
                               String couponId, String orderId, double orderAmount,
                               double discountAmount) {
        Map<String, Object> properties = new HashMap<>();
        properties.put("coupon_id", couponId);
        properties.put("order_id", orderId);
        properties.put("order_amount", orderAmount);
        properties.put("discount_amount", discountAmount);
        properties.put("roi", discountAmount > 0 ? (orderAmount - discountAmount) / discountAmount : 0);

        TrackingEvent event = TrackingEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .eventType("coupon_use")
                .userId(userId)
                .experimentId(experimentId)
                .groupId(groupId)
                .action("use")
                .timestamp(LocalDateTime.now())
                .source(applicationName)
                .properties(properties)
                .build();
        sendEvent(event);
    }

    @Async
    protected void sendEvent(TrackingEvent event) {
        try {
            String json = JSON.toJSONString(event);
            log.debug("ABTest tracking event: {}", json);
            eventRepository.saveEvent(event);
        } catch (Exception e) {
            log.error("Failed to send tracking event", e);
        }
    }

    @Data
    @Builder
    public static class TrackingEvent {
        private String eventId;
        private String eventType;
        private String userId;
        private String experimentId;
        private String groupId;
        private String action;
        private String scene;
        private LocalDateTime timestamp;
        private String source;
        private Map<String, Object> properties;
    }
}
