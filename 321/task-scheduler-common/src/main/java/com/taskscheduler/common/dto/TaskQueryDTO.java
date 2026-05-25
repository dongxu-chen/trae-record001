package com.taskscheduler.common.dto;

import lombok.Data;

@Data
public class TaskQueryDTO {

    private Integer pageNum = 1;
    private Integer pageSize = 10;
    private String taskName;
    private String taskGroup;
    private Integer taskType;
    private Integer status;
}
