package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("reconciliation_result")
public class ReconciliationResult {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String resultNo;

    private String channelCode;

    private LocalDate reconciliationDate;

    private Integer sysTotalCount;

    private BigDecimal sysTotalAmount;

    private Integer channelTotalCount;

    private BigDecimal channelTotalAmount;

    private Integer matchedCount;

    private BigDecimal matchedAmount;

    private Integer longCount;

    private BigDecimal longAmount;

    private Integer shortCount;

    private BigDecimal shortAmount;

    private Integer status;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
