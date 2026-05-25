package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeviceBinding implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;

    private String userId;

    private String deviceId;

    private String anonymousId;

    private String platform;

    private String deviceModel;

    private String os;

    private String osVersion;

    private String appId;

    private String appVersion;

    private Long bindTime;

    private Long lastActiveTime;

    private Integer eventCount;

    private String status;

    private String source;

    private String ip;

    private String country;

    private String province;

    private String city;
}
