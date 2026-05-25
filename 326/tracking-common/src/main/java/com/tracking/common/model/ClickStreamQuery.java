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
public class ClickStreamQuery implements Serializable {

    private static final long serialVersionUID = 1L;

    private String userId;

    private String anonymousId;

    private String sessionId;

    private String deviceId;

    private Long startTime;

    private Long endTime;

    private String event;

    private String platform;

    private String appId;

    private Integer page;

    private Integer pageSize;
}
