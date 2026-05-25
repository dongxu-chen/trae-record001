package com.mfa.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class BehavioralDataRequest {

    @NotNull(message = "会话ID不能为空")
    private String sessionId;

    private KeystrokeDynamics keystrokeDynamics;

    private MouseDynamics mouseDynamics;

    private String deviceFingerprint;

    private Boolean forCalibration;
}
