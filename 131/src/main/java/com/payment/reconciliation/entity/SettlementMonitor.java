package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("settlement_monitor")
public class SettlementMonitor {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String monitorNo;

    private String channelCode;

    private LocalDate settlementDate;

    private Integer status;

    private LocalDateTime expectedArrivalTime;

    private LocalDateTime actualArrivalTime;

    private BigDecimal expectedAmount;

    private BigDecimal actualAmount;

    private Long delayMinutes;

    private Integer alertLevel;

    private String alertMessage;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
