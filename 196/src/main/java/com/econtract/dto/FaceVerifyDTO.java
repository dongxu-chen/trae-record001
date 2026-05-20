package com.econtract.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;

@Data
public class FaceVerifyDTO {

    @NotBlank(message = "认证类型不能为空")
    private String verifyType;

    @NotBlank(message = "人脸照片不能为空")
    private String faceImage;
}
