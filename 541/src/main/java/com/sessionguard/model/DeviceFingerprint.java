package com.sessionguard.model;

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

    private static final long serialVersionUID = 1L;

    private String fingerprintHash;

    private String userAgent;

    private String platform;

    private String browser;

    private String browserVersion;

    private String os;

    private String osVersion;

    private String screenResolution;

    private String colorDepth;

    private String timezone;

    private String language;

    private Boolean javaEnabled;

    private Boolean cookiesEnabled;

    private Map<String, String> canvasHash;

    private Map<String, String> webglHash;

    private Map<String, String> audioHash;

    private Map<String, String> fontList;
}
