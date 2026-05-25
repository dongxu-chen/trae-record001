package com.taskscheduler.common.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class TaskLogQueryDTO {

    private Integer pageNum = 1;
    private Integer pageSize = 10;
    private Long taskId;
    private String taskName;
    private Integer triggerCode;
    private Integer executeCode;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
}
