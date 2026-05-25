package com.tracking.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserPathQuery implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long startTime;

    private Long endTime;

    private String platform;

    private String appId;

    private String startEvent;

    private String endEvent;

    private Integer maxPathLength;

    private Integer topN;

    private Boolean ignoreRepeats;

    private String userId;

    private String sessionId;
}
