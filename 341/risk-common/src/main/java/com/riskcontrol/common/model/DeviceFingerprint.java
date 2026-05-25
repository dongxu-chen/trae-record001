package com.riskcontrol.common.model;

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
public class DeviceFingerprint implements Serializable {
    private String deviceId;
    private String userAgent;
    private String platform;
    private String browser;
    private String browserVersion;
    private String os;
    private String osVersion;
    private String screenResolution;
    private String language;
    private String timezone;
    private String canvasFingerprint;
    private String webglFingerprint;
    private String fontsFingerprint;
    private String plugins;
    private String ipAddress;
    private String macAddress;
    private String hardwareConcurrency;
    private String deviceMemory;
    private Map<String, String> additionalAttributes;
    private long firstSeenTimestamp;
    private long lastSeenTimestamp;
    private int associationCount;
}
