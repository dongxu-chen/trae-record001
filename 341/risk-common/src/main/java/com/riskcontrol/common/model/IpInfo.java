package com.riskcontrol.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IpInfo implements Serializable {
    private String ipAddress;
    private String country;
    private String region;
    private String city;
    private double latitude;
    private double longitude;
    private String isp;
    private String organization;
    private String asn;
    private boolean isProxy;
    private boolean isVpn;
    private boolean isTor;
    private boolean isDataCenter;
    private boolean isBlacklisted;
    private int riskScore;
    private String proxyType;
    private long lastCheckTimestamp;
}
