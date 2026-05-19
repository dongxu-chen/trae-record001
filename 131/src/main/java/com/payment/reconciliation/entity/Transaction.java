package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("transaction")
public class Transaction {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String transactionNo;

    private String orderNo;

    private String channelCode;

    private String merchantNo;

    private BigDecimal amount;

    private BigDecimal fee;

    private Integer status;

    private String payMethod;

    private LocalDateTime transTime;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
