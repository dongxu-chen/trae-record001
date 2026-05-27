package com.grayrelease.common.dto;

import com.grayrelease.common.enums.ReleaseStatus;
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
public class ReleaseResponse {

    private String releaseId;

    private String serviceName;

    private ReleaseStrategy strategy;

    private ReleaseStatus status;

    private String stableVersion;

    private String canaryVersion;

    private Integer currentTrafficPercent;

    private LocalDateTime startTime;

    private String message;
}