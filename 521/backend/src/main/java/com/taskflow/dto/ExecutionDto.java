package com.taskflow.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class ExecutionDto {
    private Long id;
    private Long workflowId;
    private String executionId;
    private String status;
    private String triggerType;
    private Long triggerId;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
    private List<TaskExecutionDto> taskExecutions;

    @Data
    public static class TaskExecutionDto {
        private Long id;
        private Long taskId;
        private String taskKey;
        private String status;
        private Integer attempt;
        private String workerNode;
        private LocalDateTime startedAt;
        private LocalDateTime finishedAt;
        private Long durationMs;
        private String logText;
        private String errorMessage;
    }

    @Data
    public static class TriggerRequest {
        private String triggerType;
    }
}
