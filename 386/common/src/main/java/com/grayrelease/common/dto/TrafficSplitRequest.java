package com.grayrelease.common.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TrafficSplitRequest {

    private String serviceName;

    private String stableVersion;

    private String canaryVersion;

    private Integer canaryWeight;
}