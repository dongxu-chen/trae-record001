package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("discrepancy")
public class Discrepancy {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String discrepancyNo;

    private Long resultId;

    private String channelCode;

    private LocalDate reconciliationDate;

    private Integer type;

    private String orderNo;

    private String transactionNo;

    private String channelTransNo;

    private BigDecimal sysAmount;

    private BigDecimal channelAmount;

    private BigDecimal differenceAmount;

    private Integer status;

    private String handleRemark;

    private LocalDateTime handleTime;

    private String handler;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
