package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("transaction_fee")
public class TransactionFee {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String feeNo;

    private String channelCode;

    private String merchantNo;

    private String transactionNo;

    private String orderNo;

    private LocalDate settlementDate;

    private BigDecimal transAmount;

    private BigDecimal feeAmount;

    private BigDecimal feeRate;

    private Integer feeType;

    private Integer status;

    private String remark;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
