package com.analytics.util;

import com.analytics.model.UserBehaviorEvent;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.util.UUID;

public class TestDataGenerator {

    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final String[] EVENT_TYPES = {"click", "view", "purchase"};
    private static final String[] DEVICE_TYPES = {"iOS", "Android", "Web"};
    private static final String[] CHANNELS = {"app_store", "google_play", "web_direct", "ad_facebook", "ad_google", "organic"};

    public static UserBehaviorEvent generateEvent() {
        String eventType = EVENT_TYPES[(int) (Math.random() * EVENT_TYPES.length)];
        return UserBehaviorEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .userId("user_" + (int) (Math.random() * 100))
                .eventType(eventType)
                .pageId("page_" + (int) (Math.random() * 10))
                .productId(eventType.equals("purchase") ? "product_" + (int) (Math.random() * 50) : null)
                .amount(eventType.equals("purchase") ? new BigDecimal(String.format("%.2f", Math.random() * 1000)) : null)
                .deviceType(DEVICE_TYPES[(int) (Math.random() * DEVICE_TYPES.length)])
                .appVersion("1.0.0")
                .channel(CHANNELS[(int) (Math.random() * CHANNELS.length)])
                .timestamp(System.currentTimeMillis())
                .build();
    }

    public static String generateEventJson() throws Exception {
        return objectMapper.writeValueAsString(generateEvent());
    }

    public static void main(String[] args) throws Exception {
        for (int i = 0; i < 10; i++) {
            System.out.println(generateEventJson());
        }
    }
}
