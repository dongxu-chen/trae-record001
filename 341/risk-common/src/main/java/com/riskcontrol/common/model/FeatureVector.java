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
public class FeatureVector implements Serializable {
    private int eventType;
    private int isProxyIp;
    private int isBlacklistedIp;
    private int loginAttemptCount;
    private double timeSinceLastLogin;
    private int differentDevice;
    private int differentIp;
    private double velocity;
    private int unusualHour;
    private int unusualLocation;
    private int passwordLength;
    private int passwordComplexity;
    private int emailDomainRisk;
    private int phoneRisk;
    private int deviceAgeDays;
    private int accountAgeDays;
    private int historicalFraudCount;
    private int ruleScore;
    private int crossDeviceCount;
    private int ipChangeFrequency;

    public double[] toArray() {
        return new double[]{
            eventType,
            isProxyIp,
            isBlacklistedIp,
            loginAttemptCount,
            timeSinceLastLogin,
            differentDevice,
            differentIp,
            velocity,
            unusualHour,
            unusualLocation,
            passwordLength,
            passwordComplexity,
            emailDomainRisk,
            phoneRisk,
            deviceAgeDays,
            accountAgeDays,
            historicalFraudCount,
            ruleScore,
            crossDeviceCount,
            ipChangeFrequency
        };
    }

    public String[] getFeatureNames() {
        return new String[]{
            "eventType",
            "isProxyIp",
            "isBlacklistedIp",
            "loginAttemptCount",
            "timeSinceLastLogin",
            "differentDevice",
            "differentIp",
            "velocity",
            "unusualHour",
            "unusualLocation",
            "passwordLength",
            "passwordComplexity",
            "emailDomainRisk",
            "phoneRisk",
            "deviceAgeDays",
            "accountAgeDays",
            "historicalFraudCount",
            "ruleScore",
            "crossDeviceCount",
            "ipChangeFrequency"
        };
    }
}
