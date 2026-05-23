package com.emailmarketing.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import java.math.BigDecimal;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("ab_test_variant")
public class AbTestVariant extends BaseEntity {
    private Long testId;
    private String variantName;
    private String subject;
    private String content;
    private Integer weight;
    private Integer sentCount;
    private Integer openCount;
    private Integer clickCount;
    private Integer conversionCount;
    private BigDecimal openRate;
    private BigDecimal clickRate;
    private BigDecimal conversionRate;
    private Integer isWinner;
}
