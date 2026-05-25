package com.mfa.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class BehavioralBiometrics {

    private String sessionId;
    private String userId;
    private KeystrokeDynamics keystrokeDynamics;
    private MouseDynamics mouseDynamics;
    private BehavioralProfile baselineProfile;
    private BehavioralProfile currentProfile;
    private Double similarityScore;
    private Integer riskScore;
    private String riskLevel;
    private LocalDateTime timestamp;
    private String deviceFingerprint;
}
