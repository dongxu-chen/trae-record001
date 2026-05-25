package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FunnelResult implements Serializable {

    private static final long serialVersionUID = 1L;

    private String funnelName;

    private List<FunnelStep> steps;

    private Long totalUsers;

    private Long startTime;

    private Long endTime;

    private Boolean slidingWindow;

    private String slidingWindowUnit;

    private Integer slidingWindowSize;

    private List<SlidingWindowResult> slidingWindowResults;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FunnelStep implements Serializable {
        private int stepIndex;
        private String eventName;
        private Long userCount;
        private Double conversionRate;
        private Double dropOffRate;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SlidingWindowResult implements Serializable {
        private Long windowStartTime;
        private Long windowEndTime;
        private String windowLabel;
        private List<FunnelStep> steps;
        private Long totalUsers;
    }
}
