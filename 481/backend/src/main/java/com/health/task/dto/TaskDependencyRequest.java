package com.health.task.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TaskDependencyRequest {
    private String taskName;
    private String upstreamTaskName;
    private String dependencyType;
    private Integer maxWaitSeconds;
    private String description;
}
