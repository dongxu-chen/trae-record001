package com.pushplatform.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.pushplatform.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@EqualsAndHashCode(callSuper = true)
@TableName("ab_test")
public class AbTest extends BaseEntity {

    private String testCode;

    private String testName;

    private String channel;

    private Long templateAId;

    private Long templateBId;

    private Integer splitRatio;

    private Long totalTargets;

    private Long aTargets;

    private Long bTargets;

    private Integer aClicks;

    private Integer bClicks;

    private BigDecimal aClickRate;

    private BigDecimal bClickRate;

    private Integer status;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private String remark;
}
