package com.analytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserBehaviorEvent implements Serializable {
    private String eventId;
    private String userId;
    private String eventType;
    private String pageId;
    private String productId;
    private BigDecimal amount;
    private String deviceType;
    private String appVersion;
    private String channel;
    private long timestamp;
}
