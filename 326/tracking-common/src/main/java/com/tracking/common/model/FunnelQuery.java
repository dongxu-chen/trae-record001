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
public class FunnelQuery implements Serializable {

    private static final long serialVersionUID = 1L;

    private String funnelName;

    private List<String> events;

    private Long startTime;

    private Long endTime;

    private Integer windowMinutes;

    private String platform;

    private String appId;

    private String channel;

    private Boolean slidingWindow;

    private String slidingWindowUnit;

    private Integer slidingWindowSize;

    private Integer slidingWindowStep;
}
