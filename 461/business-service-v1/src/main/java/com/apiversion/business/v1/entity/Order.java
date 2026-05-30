package com.apiversion.business.v1.entity;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.math.BigDecimal;

@Data
@Schema(description = "订单实体V1")
public class Order {

    @Schema(description = "订单ID", example = "1")
    private Long id;

    @Schema(description = "用户ID", example = "1")
    private Long userId;

    @Schema(description = "订单号", example = "ORD202401010001")
    private String orderNo;

    @Schema(description = "订单金额", example = "99.99")
    private BigDecimal amount;

    @Schema(description = "订单状态", example = "CREATED")
    private String status;
}
