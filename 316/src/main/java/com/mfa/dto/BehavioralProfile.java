package com.mfa.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class BehavioralProfile {

    private Double avgHoldTime;
    private Double avgHoldTimeStdDev;
    private Double avgFlightTime;
    private Double avgFlightTimeStdDev;
    private Double typingSpeedCps;
    private Double typingSpeedStdDev;
    private Double avgMouseSpeed;
    private Double avgMouseSpeedStdDev;
    private Double avgMouseAcceleration;
    private Double pathEfficiency;
    private Double avgClickInterval;
    private Integer sampleCount;
    private Boolean isCalibrated;
    private Long lastUpdated;
}
