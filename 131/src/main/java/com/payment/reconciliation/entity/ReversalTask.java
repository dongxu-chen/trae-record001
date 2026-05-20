package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("reversal_task")
public class ReversalTask {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String taskNo;

    private Long discrepancyId;

    private String channelCode;

    private Integer taskType;

    private BigDecimal amount;

    private String orderNo;

    private Integer status;

    private Integer retryCount;

    private Integer maxRetry;

    private String errorMsg;

    private LocalDateTime handleTime;

    private String operator;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
