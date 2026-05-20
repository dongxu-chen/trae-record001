package com.econtract.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

@Data
public class SignDTO {

    @NotNull(message = "合同ID不能为空")
    private Long contractId;

    @NotBlank(message = "签名类型不能为空")
    private String signatureType;

    @NotBlank(message = "签名图片不能为空")
    private String signatureImage;

    private String signPosition;

    private String authType;

    private String smsCode;

    private String faceImage;

    private String signNote;

    private String pressureData;
}
