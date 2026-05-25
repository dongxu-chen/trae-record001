package com.taskscheduler.common.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("task_log")
public class TaskLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long taskId;

    private String taskName;

    private String taskGroup;

    private String handler;

    private String params;

    private String executorAddress;

    private Integer executeType;

    private Integer triggerCode;

    private String triggerMsg;

    private LocalDateTime triggerTime;

    private Integer executeCode;

    private String executeMsg;

    private LocalDateTime executeStartTime;

    private LocalDateTime executeEndTime;

    private Integer shardingIndex;

    private Integer shardingTotal;

    private Integer retryCount;

    private Long parentLogId;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
