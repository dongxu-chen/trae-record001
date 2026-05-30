package com.sessionguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionEvent implements Serializable {

    private static final long serialVersionUID = 1L;

    private String eventId;

    private String sessionId;

    private String userId;

    private EventType eventType;

    private String description;

    private IpContext ipContext;

    private DeviceFingerprint deviceFingerprint;

    private LocalDateTime timestamp;

    private int riskScoreAtEvent;

    public enum EventType {
        SESSION_CREATED,
        SESSION_ACCESSED,
        IP_CHANGED,
        FINGERPRINT_CHANGED,
        COOKIE_ANOMALY,
        RISK_SCORE_UPDATED,
        SESSION_INVALIDATED,
        HIJACKING_DETECTED,
        ML_ANOMALY_DETECTED,
        CONCURRENT_SESSION_DETECTED,
        THREAT_DETECTED,
        LOCATION_JUMP_DETECTED,
        BEHAVIOR_DEVIATION
    }
}
