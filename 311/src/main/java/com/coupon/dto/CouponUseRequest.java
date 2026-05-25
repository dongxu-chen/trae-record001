package com.coupon.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;

@Data
public class CouponUseRequest implements Serializable {

    private static final long serialVersionUID = 1L;

    @NotBlank(message = "发放记录ID不能为空")
    private String distributionId;

    @NotBlank(message = "订单ID不能为空")
    private String orderId;

    @NotNull(message = "订单金额不能为空")
    private BigDecimal orderAmount;
}
