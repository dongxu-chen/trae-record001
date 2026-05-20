package com.payment.reconciliation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("channel_reconciliation")
public class ChannelReconciliation {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String reconciliationNo;

    private String channelCode;

    private LocalDate reconciliationDate;

    private String fileName;

    private String filePath;

    private Integer fileType;

    private Integer totalCount;

    private BigDecimal totalAmount;

    private Integer parsedCount;

    private Integer status;

    private String errorMsg;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
