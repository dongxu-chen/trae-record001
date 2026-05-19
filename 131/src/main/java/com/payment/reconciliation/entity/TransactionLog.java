package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("transaction_log")
public class TransactionLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String transactionId;

    private String businessType;

    private String businessId;

    private Integer status;

    private Integer retryCount;

    private LocalDateTime nextRetryTime;

    private String errorMsg;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
