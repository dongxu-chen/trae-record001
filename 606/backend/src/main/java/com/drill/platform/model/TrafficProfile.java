package com.drill.platform.model;

import lombok.Data;

@Data
public class TrafficProfile {

    private int baseQps;
    private int peakQps;
    private int rampUpSeconds;
    private int sustainSeconds;
    private int rampDownSeconds;
    private TrafficPattern pattern;
    private int concurrentUsers;
    private String targetUrl;
    private String httpMethod;
    private String requestBody;
    private int connectTimeoutMs;
    private int readTimeoutMs;

    public enum TrafficPattern {
        CONSTANT, LINEAR_RAMP, SPIKE, WAVE, STEP,
        EXPONENTIAL_RAMP, LOGARITHMIC_RAMP, SIGMOID_RAMP,
        DOUBLE_STEP, GRADUAL_STEP
    }

    public static TrafficProfile defaultProfile() {
        TrafficProfile profile = new TrafficProfile();
        profile.setBaseQps(10);
        profile.setPeakQps(100);
        profile.setRampUpSeconds(10);
        profile.setSustainSeconds(30);
        profile.setRampDownSeconds(10);
        profile.setPattern(TrafficPattern.LINEAR_RAMP);
        profile.setConcurrentUsers(50);
        profile.setTargetUrl("http://localhost:8080/api/drill/target");
        profile.setHttpMethod("GET");
        profile.setConnectTimeoutMs(5000);
        profile.setReadTimeoutMs(10000);
        return profile;
    }
}
