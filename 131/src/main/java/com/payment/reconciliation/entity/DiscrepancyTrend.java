package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("discrepancy_trend")
public class DiscrepancyTrend {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String trendNo;

    private String channelCode;

    private LocalDate statisticsDate;

    private Integer totalCount;

    private BigDecimal totalAmount;

    private Integer longCount;

    private BigDecimal longAmount;

    private Integer shortCount;

    private BigDecimal shortAmount;

    private Integer amountMismatchCount;

    private BigDecimal amountMismatchAmount;

    private Integer resolvedCount;

    private BigDecimal resolvedAmount;

    private LocalDateTime createTime;
}
