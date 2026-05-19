package com.payment.reconciliation.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class FeeCalculateDTO {

    @NotBlank(message = "渠道编码不能为空")
    private String channelCode;

    private String merchantNo;

    @NotNull(message = "结算日期不能为空")
    private LocalDate settlementDate;

    private BigDecimal totalAmount;
}
