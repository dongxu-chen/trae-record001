package com.grayrelease.common.dto;

import com.grayrelease.common.enums.ExperimentStatus;
import com.grayrelease.common.enums.ReleaseStrategy;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExperimentResponse {

    private String experimentId;

    private String name;

    private String serviceName;

    private String experimentGroup;

    private ReleaseStrategy strategy;

    private ExperimentStatus status;

    private String stableVersion;

    private String experimentVersion;

    private int currentTrafficPercent;

    private int maxTrafficPercent;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private String message;
}