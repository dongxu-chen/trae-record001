package com.payment.reconciliation.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.time.LocalDate;

@Data
public class ReconciliationExecuteDTO {

    @NotBlank(message = "渠道编码不能为空")
    private String channelCode;

    @NotNull(message = "对账日期不能为空")
    private LocalDate reconciliationDate;
}
