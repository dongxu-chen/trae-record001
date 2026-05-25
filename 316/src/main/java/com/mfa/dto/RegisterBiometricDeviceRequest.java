package com.mfa.dto;

import com.mfa.enums.FactorType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class RegisterBiometricDeviceRequest {

    @NotNull(message = "认证因子类型不能为空")
    private FactorType factorType;

    @NotBlank(message = "设备名称不能为空")
    private String deviceName;

    private String deviceModel;

    private String deviceOs;

    private String deviceBrowser;

    private String deviceInfo;

    @NotBlank(message = "生物特征数据不能为空")
    private String biometricTemplate;

    private String devicePublicKey;
}
