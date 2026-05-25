package com.taskscheduler.common.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class GanttTaskDTO {
    private Long id;
    private Long taskId;
    private String taskName;
    private String taskGroup;
    private Integer shardingIndex;
    private Integer shardingTotal;
    private String executorAddress;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer executeCode;
    private String executeMsg;
    private Long duration;
    private String status;
    private String priority;
}
