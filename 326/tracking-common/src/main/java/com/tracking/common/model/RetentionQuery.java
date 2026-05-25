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
public class RetentionQuery implements Serializable {

    private static final long serialVersionUID = 1L;

    private String retentionType;

    private String initialEvent;

    private String returnEvent;

    private Long startTime;

    private Long endTime;

    private List<Integer> retentionDays;

    private String platform;

    private String appId;

    private String channel;

    private String groupBy;

    private Boolean useCache;
}
