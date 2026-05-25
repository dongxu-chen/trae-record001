package com.riskcontrol.common.model;

import com.riskcontrol.common.enums.EventType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RiskEvent implements Serializable {
    private String eventId;
    private String userId;
    private String account;
    private EventType eventType;
    private long eventTimestamp;
    private String ipAddress;
    private DeviceFingerprint deviceFingerprint;
    private IpInfo ipInfo;
    private String email;
    private String phone;
    private String username;
    private String oldPasswordHash;
    private String newPasswordHash;
    private String sessionId;
    private String referer;
    private String userAgent;
    private int loginAttemptCount;
    private long lastLoginTimestamp;
    private String lastLoginIp;
    private String lastLoginDeviceId;
    private double velocityKmPerHour;
    private Map<String, Object> additionalData;
    private int ruleScore;
    private int mlScore;
    private int finalScore;
}
