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
public class MouseDynamics {

    private List<MouseMoveEvent> moveEvents;
    private List<MouseClickEvent> clickEvents;
    private Double avgSpeed;
    private Double avgAcceleration;
    private Double avgDirectionChange;
    private Double avgClickInterval;
    private Integer totalMoves;
    private Integer totalClicks;
    private Long durationMs;
    private Double pathLength;
    private Double directPathLength;
    private Double pathEfficiency;
    private List<Double> speedProfile;
    private List<Double> accelerationProfile;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MouseMoveEvent {
        private Integer x;
        private Integer y;
        private Long timestamp;
        private Double speed;
        private Double acceleration;
        private Double direction;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MouseClickEvent {
        private Integer x;
        private Integer y;
        private Long timestamp;
        private String button;
        private Long pressDuration;
    }
}
