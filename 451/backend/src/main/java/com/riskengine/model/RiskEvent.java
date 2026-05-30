package com.riskengine.model;

import lombok.Data;
import java.io.Serializable;
import java.util.Map;

@Data
public class RiskEvent implements Serializable {
    private String eventId;
    private String eventType;
    private String userId;
    private String ip;
    private String deviceId;
    private Long timestamp;
    private Map<String, Object> payload;

    public RiskEvent() {
        this.timestamp = System.currentTimeMillis();
    }
}
