package com.mfa.dto;

import com.mfa.enums.FactorType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BiometricDeviceDTO {

    private Long id;
    private FactorType factorType;
    private String name;
    private String deviceName;
    private String deviceModel;
    private String deviceOs;
    private String deviceBrowser;
    private String deviceInfo;
    private LocalDateTime createdAt;
    private LocalDateTime lastUsedAt;
    private LocalDateTime lastSyncedAt;
    private boolean enabled;
    private boolean verified;
    private boolean revoked;
    private String revokeReason;
    private LocalDateTime revokedAt;
}
