package com.mfa.dto;

import com.mfa.enums.FactorType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class VerifyCodeRequest {

    @NotBlank(message = "会话ID不能为空")
    private String sessionId;

    @NotNull(message = "认证因子类型不能为空")
    private FactorType factorType;

    @NotBlank(message = "验证码不能为空")
    private String code;
}
