package com.mfa.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class KeystrokeDynamics {

    private String targetField;
    private List<KeystrokeEvent> events;
    private Double avgHoldTime;
    private Double avgFlightTime;
    private Double stdDevHoldTime;
    private Double stdDevFlightTime;
    private List<Double> holdTimes;
    private List<Double> flightTimes;
    private Integer totalKeystrokes;
    private Long durationMs;
    private Double typingSpeedCps;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class KeystrokeEvent {
        private String key;
        private Long keyDownTime;
        private Long keyUpTime;
        private Double holdTime;
        private Integer keyCode;
    }
}
