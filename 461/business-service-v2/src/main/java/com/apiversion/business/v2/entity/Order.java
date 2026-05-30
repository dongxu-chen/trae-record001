package com.apiversion.business.v2.entity;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Schema(description = "订单信息V2")
public class Order {

    @Schema(description = "订单ID")
    private Long id;

    @Schema(description = "订单编号")
    private String orderNo;

    @Schema(description = "用户ID")
    private Long userId;

    @Schema(description = "订单金额")
    private BigDecimal amount;

    @Schema(description = "订单状态")
    private String status;

    @Schema(description = "支付时间")
    private LocalDateTime payTime;

    @Schema(description = "配送时间")
    private LocalDateTime deliveryTime;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;

    @Schema(description = "更新时间")
    private LocalDateTime updateTime;
}
