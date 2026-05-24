package com.homestay.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("coupon")
public class Coupon {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String name;

    private String code;

    private Integer type;

    private BigDecimal discountAmount;

    private BigDecimal discountPercent;

    private BigDecimal minAmount;

    private Integer totalCount;

    private Integer usedCount;

    private Integer perUserLimit;

    private String groupCode;

    private LocalDateTime validStartTime;

    private LocalDateTime validEndTime;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
