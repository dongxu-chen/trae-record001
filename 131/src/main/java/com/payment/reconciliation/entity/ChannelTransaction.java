package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("channel_transaction")
public class ChannelTransaction {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long reconciliationId;

    private String channelTransNo;

    private String channelCode;

    private String merchantNo;

    private String orderNo;

    private BigDecimal amount;

    private BigDecimal fee;

    private Integer status;

    private LocalDateTime transTime;

    private Integer matched;

    private LocalDateTime createTime;
}
