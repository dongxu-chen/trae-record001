package com.taskscheduler.common.dto;

import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
public class TaskExecuteResult implements Serializable {

    private Long logId;

    private Integer executeCode;

    private String executeMsg;

    private LocalDateTime executeStartTime;

    private LocalDateTime executeEndTime;

    private Integer shardingIndex;

    public static TaskExecuteResult success(Long logId) {
        TaskExecuteResult result = new TaskExecuteResult();
        result.setLogId(logId);
        result.setExecuteCode(0);
        result.setExecuteMsg("执行成功");
        result.setExecuteStartTime(LocalDateTime.now());
        result.setExecuteEndTime(LocalDateTime.now());
        return result;
    }

    public static TaskExecuteResult fail(Long logId, String errorMsg) {
        TaskExecuteResult result = new TaskExecuteResult();
        result.setLogId(logId);
        result.setExecuteCode(500);
        result.setExecuteMsg(errorMsg);
        result.setExecuteStartTime(LocalDateTime.now());
        result.setExecuteEndTime(LocalDateTime.now());
        return result;
    }
}
