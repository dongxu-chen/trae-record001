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
public class UserSessionStats implements Serializable {

    private static final long serialVersionUID = 1L;

    private String userId;

    private String anonymousId;

    private Integer totalSessions;

    private Long avgSessionInterval;

    private Long medianSessionInterval;

    private Long p75SessionInterval;

    private Long p90SessionInterval;

    private Long p95SessionInterval;

    private Long minSessionInterval;

    private Long maxSessionInterval;

    private List<Long> sessionIntervals;

    private Long dynamicSessionTimeout;

    private Integer sampleSize;

    private Long lastUpdateTime;

    private String platform;

    private String appId;
}
