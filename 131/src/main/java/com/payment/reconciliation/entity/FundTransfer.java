package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("fund_transfer")
public class FundTransfer {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String transferNo;

    private String requestId;

    private Long discrepancyId;

    private String channelCode;

    private Integer transferType;

    private BigDecimal amount;

    private String fromAccount;

    private String toAccount;

    private String bankOrderNo;

    private Integer status;

    private String remark;

    private LocalDateTime transferTime;

    private String operator;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
