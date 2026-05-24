package com.homestay.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("order_info")
public class OrderInfo {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String orderNo;

    private Long userId;

    private Long houseId;

    private Long hostId;

    private LocalDate checkInDate;

    private LocalDate checkOutDate;

    private Integer guestCount;

    private Integer nightCount;

    private BigDecimal totalPrice;

    private BigDecimal cleaningFee;

    private BigDecimal couponDiscount;

    private BigDecimal payAmount;

    private Integer status;

    private String contactName;

    private String contactPhone;

    private String remark;

    private Long couponId;

    private String couponIds;

    private String payMethod;

    private LocalDateTime payTime;

    private LocalDateTime cancelTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic
    private Integer deleted;
}
