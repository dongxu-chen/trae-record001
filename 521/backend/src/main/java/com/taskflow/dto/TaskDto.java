package com.taskflow.dto;

import lombok.Data;
import java.util.List;

@Data
public class TaskDto {
    private Long id;
    private String taskKey;
    private String taskName;
    private String taskType;
    private String taskConfig;
    private Integer taskPriority;
    private Integer retryCount;
    private Integer retryInterval;
    private String retryStrategy;
    private Integer timeoutSeconds;
    private List<String> upstreamKeys;
    private List<String> dataProducts;
    private Double positionX;
    private Double positionY;

    public enum RetryStrategy {
        FIXED,
        EXPONENTIAL,
        LINEAR,
        NONE
    }

    public enum FailureType {
        NETWORK_ERROR,
        TIMEOUT,
        BUSINESS_ERROR,
        RESOURCE_ERROR,
        UNKNOWN
    }
}
