package com.mfa.service.impl;

import com.mfa.config.MfaProperties;
import com.mfa.dto.RegisterUserRequest;
import com.mfa.dto.TotpSetupResponse;
import com.mfa.dto.WebAuthnCredential;
import com.mfa.dto.WebAuthnOptionsResponse;
import com.mfa.entity.AuthFactor;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import com.mfa.repository.AuthFactorRepository;
import com.mfa.repository.UserRepository;
import com.mfa.service.TotpService;
import com.mfa.service.UserService;
import com.mfa.service.WebAuthnService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.codec.binary.Base32;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;
    private final AuthFactorRepository authFactorRepository;
    private final PasswordEncoder passwordEncoder;
    private final TotpService totpService;
    private final WebAuthnService webAuthnService;
    private final MfaProperties mfaProperties;

    @Override
    @Transactional
    public User registerUser(RegisterUserRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new IllegalArgumentException("用户名已存在");
        }
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new IllegalArgumentException("邮箱已被注册");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setEmail(request.getEmail());
        user.setPhone(request.getPhone());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setEnabled(true);
        user.setAccountLocked(false);

        User saved = userRepository.save(user);
        log.info("User registered: {}", saved.getUsername());

        return saved;
    }

    @Override
    public Optional<User> findByUsername(String username) {
        return userRepository.findByUsername(username);
    }

    @Override
    public List<AuthFactor> getUserFactors(Long userId) {
        return authFactorRepository.findByUserIdAndEnabledTrue(userId);
    }

    @Override
    public TotpSetupResponse setupTotp(User user, String issuer) {
        TotpSetupResponse setup = totpService.generateSecret(user.getUsername(), issuer);

        List<AuthFactor> existingFactors = authFactorRepository.findByUserIdAndFactorType(
                user.getId(), FactorType.TOTP);

        if (!existingFactors.isEmpty()) {
            AuthFactor existing = existingFactors.get(0);
            existing.setSecret(setup.getSecret());
            existing.setVerified(false);
            authFactorRepository.save(existing);
        } else {
            AuthFactor factor = new AuthFactor();
            factor.setUser(user);
            factor.setFactorType(FactorType.TOTP);
            factor.setName("Google Authenticator");
            factor.setSecret(setup.getSecret());
            factor.setEnabled(true);
            factor.setVerified(false);
            authFactorRepository.save(factor);
        }

        log.info("TOTP setup initiated for user: {}", user.getUsername());
        return setup;
    }

    @Override
    @Transactional
    public boolean verifyTotpSetup(User user, String code) {
        List<AuthFactor> factors = authFactorRepository.findByUserIdAndFactorType(
                user.getId(), FactorType.TOTP);

        if (factors.isEmpty()) {
            return false;
        }

        AuthFactor factor = factors.get(0);
        boolean valid = totpService.verifyCode(factor.getSecret(), code);

        if (valid) {
            factor.setVerified(true);
            authFactorRepository.save(factor);
            log.info("TOTP setup verified for user: {}", user.getUsername());
        }

        return valid;
    }

    @Override
    public WebAuthnOptionsResponse setupWebAuthn(String sessionId, User user) {
        return webAuthnService.generateRegistrationOptions(sessionId, user);
    }

    @Override
    @Transactional
    public boolean verifyWebAuthnSetup(String sessionId, WebAuthnCredential credential, User user) {
        return webAuthnService.verifyRegistration(sessionId, credential, user);
    }

    @Override
    @Transactional
    public boolean setupBiometric(User user, FactorType factorType, String biometricTemplate) {
        if (factorType != FactorType.BIOMETRIC_FINGERPRINT && factorType != FactorType.BIOMETRIC_FACE) {
            throw new IllegalArgumentException("Invalid biometric factor type");
        }

        List<AuthFactor> existingFactors = authFactorRepository.findByUserIdAndFactorType(
                user.getId(), factorType);

        AuthFactor factor;
        if (!existingFactors.isEmpty()) {
            factor = existingFactors.get(0);
        } else {
            factor = new AuthFactor();
            factor.setUser(user);
            factor.setFactorType(factorType);
            factor.setName(factorType == FactorType.BIOMETRIC_FINGERPRINT ? "指纹识别" : "人脸识别");
            factor.setEnabled(true);
        }

        factor.setSecret(biometricTemplate);
        factor.setVerified(true);
        authFactorRepository.save(factor);

        log.info("{} setup completed for user: {}", factorType, user.getUsername());
        return true;
    }

    @Override
    @Transactional
    public void deleteFactor(Long userId, Long factorId) {
        AuthFactor factor = authFactorRepository.findById(factorId)
                .orElseThrow(() -> new IllegalArgumentException("认证因子不存在"));

        if (!factor.getUser().getId().equals(userId)) {
            throw new IllegalArgumentException("无权删除该认证因子");
        }

        authFactorRepository.delete(factor);
        log.info("Auth factor deleted: {} for user: {}", factor.getFactorType(), factor.getUser().getUsername());
    }

    @Override
    public User getCurrentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            return null;
        }
        String username = authentication.getName();
        return userRepository.findByUsername(username).orElse(null);
    }
}
