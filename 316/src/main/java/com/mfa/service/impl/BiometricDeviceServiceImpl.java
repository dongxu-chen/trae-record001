package com.mfa.service.impl;

import com.mfa.dto.BiometricDeviceDTO;
import com.mfa.dto.RegisterBiometricDeviceRequest;
import com.mfa.entity.AuthFactor;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import com.mfa.repository.AuthFactorRepository;
import com.mfa.service.BiometricDeviceService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class BiometricDeviceServiceImpl implements BiometricDeviceService {

    private final AuthFactorRepository authFactorRepository;

    @Override
    public List<BiometricDeviceDTO> getUserDevices(User user) {
        List<AuthFactor> biometricFactors = authFactorRepository.findByUserIdAndEnabledTrue(user.getId())
                .stream()
                .filter(f -> f.getFactorType() == FactorType.BIOMETRIC_FINGERPRINT
                        || f.getFactorType() == FactorType.BIOMETRIC_FACE)
                .toList();

        return biometricFactors.stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional
    public BiometricDeviceDTO registerDevice(User user, RegisterBiometricDeviceRequest request) {
        if (request.getFactorType() != FactorType.BIOMETRIC_FINGERPRINT
                && request.getFactorType() != FactorType.BIOMETRIC_FACE) {
            throw new IllegalArgumentException("仅支持生物识别设备");
        }

        AuthFactor factor = new AuthFactor();
        factor.setUser(user);
        factor.setFactorType(request.getFactorType());
        factor.setName(request.getDeviceName());
        factor.setDeviceName(request.getDeviceName());
        factor.setDeviceModel(request.getDeviceModel());
        factor.setDeviceOs(request.getDeviceOs());
        factor.setDeviceBrowser(request.getDeviceBrowser());
        factor.setDeviceInfo(request.getDeviceInfo());
        factor.setDevicePublicKey(request.getDevicePublicKey());
        factor.setSecret(request.getBiometricTemplate());
        factor.setVerified(true);
        factor.setEnabled(true);
        factor.setRevoked(false);
        factor.setLastSyncedAt(LocalDateTime.now());

        AuthFactor saved = authFactorRepository.save(factor);
        log.info("Registered {} device for user: {}, deviceId: {}",
                request.getFactorType(), user.getUsername(), saved.getId());

        return convertToDTO(saved);
    }

    @Override
    @Transactional
    public BiometricDeviceDTO updateDeviceName(User user, Long deviceId, String name) {
        AuthFactor factor = getDeviceAndValidateOwnership(user, deviceId);
        factor.setName(name);
        factor.setDeviceName(name);
        AuthFactor saved = authFactorRepository.save(factor);
        log.info("Updated device name for device: {}, user: {}", deviceId, user.getUsername());
        return convertToDTO(saved);
    }

    @Override
    @Transactional
    public void revokeDevice(User user, Long deviceId, String reason) {
        AuthFactor factor = getDeviceAndValidateOwnership(user, deviceId);
        factor.setEnabled(false);
        factor.setRevoked(true);
        factor.setRevokeReason(reason);
        factor.setRevokedAt(LocalDateTime.now());
        authFactorRepository.save(factor);
        log.info("Revoked device: {} for user: {}, reason: {}", deviceId, user.getUsername(), reason);
    }

    @Override
    @Transactional
    public void syncDevice(User user, Long deviceId, String devicePublicKey) {
        AuthFactor factor = getDeviceAndValidateOwnership(user, deviceId);
        if (devicePublicKey != null) {
            factor.setDevicePublicKey(devicePublicKey);
        }
        factor.setLastSyncedAt(LocalDateTime.now());
        authFactorRepository.save(factor);
        log.debug("Synced device: {} for user: {}", deviceId, user.getUsername());
    }

    private AuthFactor getDeviceAndValidateOwnership(User user, Long deviceId) {
        AuthFactor factor = authFactorRepository.findById(deviceId)
                .orElseThrow(() -> new IllegalArgumentException("设备不存在"));

        if (!factor.getUser().getId().equals(user.getId())) {
            throw new SecurityException("无权操作该设备");
        }

        if (factor.getFactorType() != FactorType.BIOMETRIC_FINGERPRINT
                && factor.getFactorType() != FactorType.BIOMETRIC_FACE) {
            throw new IllegalArgumentException("该设备不是生物识别设备");
        }

        return factor;
    }

    private BiometricDeviceDTO convertToDTO(AuthFactor factor) {
        return BiometricDeviceDTO.builder()
                .id(factor.getId())
                .factorType(factor.getFactorType())
                .name(factor.getName())
                .deviceName(factor.getDeviceName())
                .deviceModel(factor.getDeviceModel())
                .deviceOs(factor.getDeviceOs())
                .deviceBrowser(factor.getDeviceBrowser())
                .deviceInfo(factor.getDeviceInfo())
                .createdAt(factor.getCreatedAt())
                .lastUsedAt(factor.getLastUsedAt())
                .lastSyncedAt(factor.getLastSyncedAt())
                .enabled(factor.isEnabled())
                .verified(factor.isVerified())
                .revoked(factor.isRevoked())
                .revokeReason(factor.getRevokeReason())
                .revokedAt(factor.getRevokedAt())
                .build();
    }
}
