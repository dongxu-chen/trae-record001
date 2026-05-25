package com.taskscheduler.common.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("task_info")
public class TaskInfo {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String taskName;

    private String taskGroup;

    private Integer taskType;

    private String cronExpression;

    private String handler;

    private String params;

    private Integer executorRouteStrategy;

    private Integer taskTimeout;

    private Integer maxRetryCount;

    private Integer retryInterval;

    private Integer shardingTotal;

    private String shardingParam;

    private String dagDependencies;

    private Integer status;

    private LocalDateTime lastExecuteTime;

    private LocalDateTime nextExecuteTime;

    private String description;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
