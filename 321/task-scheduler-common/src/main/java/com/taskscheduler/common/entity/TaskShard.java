package com.taskscheduler.common.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("task_shard")
public class TaskShard {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long taskId;

    private Long logId;

    private Integer shardIndex;

    private Integer shardTotal;

    private String shardParam;

    private String executorAddress;

    private Integer status;

    private Integer retryCount;

    private LocalDateTime executeStartTime;

    private LocalDateTime executeEndTime;

    private String executeMsg;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
