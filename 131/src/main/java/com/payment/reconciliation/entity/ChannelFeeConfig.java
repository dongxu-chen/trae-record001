package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("channel_fee_config")
public class ChannelFeeConfig {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String channelCode;

    private String merchantNo;

    private Integer feeType;

    private BigDecimal feeRate;

    private BigDecimal fixedFee;

    private BigDecimal minFee;

    private BigDecimal maxFee;

    private BigDecimal startAmount;

    private BigDecimal endAmount;

    private Integer status;

    private LocalDateTime effectiveDate;

    private LocalDateTime expireDate;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
