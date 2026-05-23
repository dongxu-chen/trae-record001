package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("delivery_report")
public class DeliveryReport {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long taskId;
    private String domain;
    private Integer totalSent;
    private Integer delivered;
    private Integer bounced;
    private Integer complained;
    private Integer opened;
    private Integer clicked;
    private BigDecimal deliveryRate;
    private BigDecimal openRate;
    private BigDecimal clickRate;
    private Integer avgDelaySeconds;
    private String delayDistribution;
    private LocalDate reportDate;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
