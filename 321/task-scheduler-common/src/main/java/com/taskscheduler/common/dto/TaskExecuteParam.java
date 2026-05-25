package com.taskscheduler.common.dto;

import lombok.Data;

import java.io.Serializable;

@Data
public class TaskExecuteParam implements Serializable {

    private Long taskId;

    private Long logId;

    private String taskName;

    private String taskGroup;

    private String handler;

    private String params;

    private Integer shardingIndex;

    private Integer shardingTotal;

    private String shardingParam;

    private Integer timeout;

    private Integer retryCount;
}
