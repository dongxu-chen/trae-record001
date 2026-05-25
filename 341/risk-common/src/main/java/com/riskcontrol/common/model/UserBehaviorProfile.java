package com.riskcontrol.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Set;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserBehaviorProfile implements Serializable {
    private String userId;
    private Set<String> commonIpAddresses;
    private Set<String> commonDeviceIds;
    private Set<String> commonLocations;
    private int usualLoginStartHour;
    private int usualLoginEndHour;
    private int totalLoginCount;
    private int failedLoginCount;
    private int passwordChangeCount;
    private long accountCreationTimestamp;
    private long lastActiveTimestamp;
    private int fraudFlagCount;
    private double averageSessionDuration;
    private Set<String> commonCountries;
}
