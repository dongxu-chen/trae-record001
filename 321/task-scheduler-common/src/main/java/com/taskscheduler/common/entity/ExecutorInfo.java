package com.taskscheduler.common.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("executor_info")
public class ExecutorInfo {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String executorName;

    private String executorAddress;

    private String appName;

    private Integer status;

    private LocalDateTime heartbeatTime;

    private LocalDateTime registerTime;

    private String description;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
