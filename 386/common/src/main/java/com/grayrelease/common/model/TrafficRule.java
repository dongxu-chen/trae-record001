package com.grayrelease.common.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TrafficRule {

    private String serviceName;

    private String stableVersion;

    private String canaryVersion;

    private Integer canaryWeight;

    private Map<String, String> headers;

    private Map<String, String> cookies;

    private String matchExpression;

    private List<TrafficTarget> targets;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TrafficTarget {
        private String version;
        private String host;
        private Integer port;
        private Integer weight;
    }
}