package com.econtract.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

@Data
public class SignerDTO {

    @NotNull(message = "签署人ID不能为空")
    private Long signerId;

    @NotBlank(message = "签署人姓名不能为空")
    private String signerName;

    @NotBlank(message = "签署人手机号不能为空")
    private String signerPhone;

    @NotNull(message = "签署顺序不能为空")
    private Integer signOrder;

    private String signPosition;
}
