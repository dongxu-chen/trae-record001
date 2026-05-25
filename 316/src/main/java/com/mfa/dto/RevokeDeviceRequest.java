package com.mfa.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class RevokeDeviceRequest {

    @NotBlank(message = "解绑原因不能为空")
    private String reason;
}
