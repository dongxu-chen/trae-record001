package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("ab_test")
public class AbTest extends BaseEntity {
    private String name;
    private Long templateId;
    private Long groupId;
    private Integer testType;
    private Integer sampleSize;
    private Integer totalSize;
    private Long winnerId;
    private Integer status;
    private Integer metricType;
    private BigDecimal confidenceLevel;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
}
