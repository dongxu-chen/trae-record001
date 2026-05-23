package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("category_preference")
public class CategoryPreference {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long recipientId;
    private String email;
    private String categoryCode;
    private BigDecimal preferenceScore;
    private Integer viewCount;
    private Integer clickCount;
    private Integer conversionCount;
    private LocalDateTime lastBehaviorTime;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
