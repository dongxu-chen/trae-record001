package com.payment.reconciliation.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.math.BigDecimal;

@Data
public class FundTransferDTO {

    @NotBlank(message = "唯一请求ID不能为空")
    private String requestId;

    private Long discrepancyId;

    @NotBlank(message = "渠道编码不能为空")
    private String channelCode;

    @NotNull(message = "调拨类型不能为空")
    private Integer transferType;

    @NotNull(message = "调拨金额不能为空")
    private BigDecimal amount;

    @NotBlank(message = "出款账户不能为空")
    private String fromAccount;

    @NotBlank(message = "入款账户不能为空")
    private String toAccount;

    private String remark;

    @NotBlank(message = "操作人不能为空")
    private String operator;
}
