package com.mfa.service;

import com.mfa.dto.BiometricDeviceDTO;
import com.mfa.dto.RegisterBiometricDeviceRequest;
import com.mfa.entity.User;

import java.util.List;

public interface BiometricDeviceService {

    List<BiometricDeviceDTO> getUserDevices(User user);

    BiometricDeviceDTO registerDevice(User user, RegisterBiometricDeviceRequest request);

    BiometricDeviceDTO updateDeviceName(User user, Long deviceId, String name);

    void revokeDevice(User user, Long deviceId, String reason);

    void syncDevice(User user, Long deviceId, String devicePublicKey);
}
