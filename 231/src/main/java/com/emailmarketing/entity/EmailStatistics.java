package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("email_statistics")
public class EmailStatistics {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long taskId;
    private Integer totalSent;
    private Integer totalOpened;
    private Integer totalClicked;
    private Integer totalUnsubscribed;
    private BigDecimal openRate;
    private BigDecimal clickRate;
    private BigDecimal unsubscribeRate;
    private LocalDate statisticsDate;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
