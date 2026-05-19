package com.payment.reconciliation.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

@Data
public class DiscrepancyHandleDTO {

    @NotNull(message = "差错记录ID不能为空")
    private Long discrepancyId;

    @NotNull(message = "处理状态不能为空")
    private Integer status;

    private String handleRemark;

    @NotBlank(message = "处理人不能为空")
    private String handler;
}
