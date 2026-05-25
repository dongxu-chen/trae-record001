package com.survey.model;

import lombok.Data;

@Data
public class DeviceInfo {
    private String userAgent;
    private String deviceType;
    private String os;
    private String browser;
    private String screenResolution;
    private String language;
}
