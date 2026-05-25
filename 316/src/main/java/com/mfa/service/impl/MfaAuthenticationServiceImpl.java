package com.mfa.service.impl;

import com.mfa.config.MfaProperties;
import com.mfa.dto.*;
import com.mfa.entity.AuthFactor;
import com.mfa.entity.User;
import com.mfa.enums.AuthStatus;
import com.mfa.enums.FactorType;
import com.mfa.repository.AuthFactorRepository;
import com.mfa.repository.UserRepository;
import com.mfa.service.*;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class MfaAuthenticationServiceImpl implements MfaAuthenticationService {

    private final UserRepository userRepository;
    private final AuthFactorRepository authFactorRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuthSessionService authSessionService;
    private final RiskAssessmentService riskAssessmentService;
    private final AdaptiveAuthenticationService adaptiveAuthService;
    private final AuthPolicyService authPolicyService;
    private final AuditLogService auditLogService;
    private final VerificationCodeService verificationCodeService;
    private final SmsService smsService;
    private final EmailService emailService;
    private final TotpService totpService;
    private final WebAuthnService webAuthnService;
    private final BiometricService biometricService;
    private final JwtService jwtService;
    private final MfaProperties mfaProperties;

    @Override
    @Transactional
    public AuthResponse login(LoginRequest request, HttpServletRequest httpRequest) {
        log.info("Login attempt for user: {}", request.getUsername());

        User user = userRepository.findByUsernameWithFactors(request.getUsername())
                .orElse(null);

        if (user == null || !passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            auditLogService.logAuthentication("unknown", user, null,
                    AuthStatus.FAILED, "Invalid username or password", httpRequest, null);
            log.warn("Login failed for user: {} - invalid credentials", request.getUsername());
            return AuthResponse.builder()
                    .status(AuthStatus.FAILED)
                    .message("用户名或密码错误")
                    .build();
        }

        if (!user.isEnabled() || user.isAccountLocked()) {
            auditLogService.logAuthentication("unknown", user, null,
                    AuthStatus.FAILED, "Account disabled or locked", httpRequest, null);
            log.warn("Login failed for user: {} - account disabled or locked", request.getUsername());
            return AuthResponse.builder()
                    .status(AuthStatus.FAILED)
                    .message("账号已被禁用或锁定")
                    .build();
        }

        RiskAssessment riskAssessment = adaptiveAuthService.assessAdaptiveRisk(user, httpRequest);
        String authLevel = adaptiveAuthService.getAuthenticationLevel(riskAssessment);

        if (adaptiveAuthService.shouldBypassMfa(user, httpRequest, riskAssessment)) {
            log.info("MFA bypassed for user: {} due to low risk ({})", user.getUsername(), authLevel);

            AuthSession tempSession = authSessionService.createSession(user, riskAssessment);
            tempSession.setStatus(AuthStatus.SUCCESS);
            authSessionService.updateSession(tempSession);

            auditLogService.logAuthentication(tempSession.getSessionId(), user, null,
                    AuthStatus.SUCCESS, "Authentication successful (adaptive bypass - trusted device)",
                    httpRequest, riskAssessment);

            String token = jwtService.generateToken(user);
            authSessionService.invalidateSession(tempSession.getSessionId());

            return AuthResponse.builder()
                    .sessionId(tempSession.getSessionId())
                    .status(AuthStatus.SUCCESS)
                    .message("可信设备登录成功")
                    .token(token)
                    .mfaRequired(false)
                    .currentStep(1)
                    .totalSteps(1)
                    .riskScore(riskAssessment.getScore())
                    .riskLevel(riskAssessment.getLevel())
                    .adaptiveAuthLevel(authLevel)
                    .build();
        }

        List<FactorType> adaptiveRequiredFactors = adaptiveAuthService.determineAdaptiveRequiredFactors(
                user, riskAssessment);

        riskAssessment.setStepUpRequired(adaptiveAuthService.shouldStepUpAuthentication(
                user, riskAssessment, 0));

        AuthSession session = authSessionService.createSession(user, riskAssessment);
        session.setRequiredFactors(adaptiveRequiredFactors);
        authSessionService.updateSession(session);

        auditLogService.logAuthentication(session.getSessionId(), user, null,
                AuthStatus.IN_PROGRESS,
                String.format("Password authenticated, adaptive MFA required (level: %s)", authLevel),
                httpRequest, riskAssessment);

        List<FactorType> availableFactors = authFactorRepository.findVerifiedFactorTypesByUserId(user.getId());

        if (availableFactors.isEmpty() || adaptiveRequiredFactors.isEmpty()) {
            log.info("User {} has no MFA factors configured, logging in with password only", user.getUsername());
            session.setStatus(AuthStatus.SUCCESS);
            authSessionService.updateSession(session);
            auditLogService.logAuthentication(session.getSessionId(), user, null,
                    AuthStatus.SUCCESS, "Authentication successful (no MFA configured)",
                    httpRequest, riskAssessment);

            String token = jwtService.generateToken(user);
            authSessionService.invalidateSession(session.getSessionId());

            return AuthResponse.builder()
                    .sessionId(session.getSessionId())
                    .status(AuthStatus.SUCCESS)
                    .message("认证成功")
                    .token(token)
                    .mfaRequired(false)
                    .currentStep(1)
                    .totalSteps(1)
                    .riskScore(riskAssessment.getScore())
                    .riskLevel(riskAssessment.getLevel())
                    .adaptiveAuthLevel(authLevel)
                    .build();
        }

        log.info("Adaptive MFA required for user: {}, level: {}, required factors: {}",
                user.getUsername(), authLevel, adaptiveRequiredFactors);

        return buildAuthResponse(session, authLevel);
    }

    @Override
    public AuthResponse sendCode(SendCodeRequest request, HttpServletRequest httpRequest) {
        log.info("Send code request for session: {}, factor: {}", request.getSessionId(), request.getFactorType());

        AuthSession session = authSessionService.getSession(request.getSessionId())
                .orElse(null);

        if (session == null) {
            return AuthResponse.builder()
                    .sessionId(request.getSessionId())
                    .status(AuthStatus.FAILED)
                    .message("会话不存在或已过期")
                    .build();
        }

        User user = session.getUser();
        FactorType factorType = request.getFactorType();

        if (session.isFactorCompleted(factorType)) {
            return AuthResponse.builder()
                    .sessionId(session.getSessionId())
                    .status(session.getStatus())
                    .message("该认证因子已验证")
                    .requiredFactors(session.getRequiredFactors())
                    .completedFactors(session.getCompletedFactors())
                    .build();
        }

        String target;
        String code;

        switch (factorType) {
            case SMS -> {
                target = user.getPhone();
                if (target == null || target.isEmpty()) {
                    return AuthResponse.builder()
                            .sessionId(session.getSessionId())
                            .status(AuthStatus.FAILED)
                            .message("用户未配置手机号")
                            .build();
                }
                code = verificationCodeService.generateCode(
                        session.getSessionId(), target,
                        mfaProperties.getSms().getCodeLength(),
                        mfaProperties.getSms().getExpireMinutes());
                smsService.sendVerificationCode(target, code);
            }
            case EMAIL -> {
                target = user.getEmail();
                code = verificationCodeService.generateCode(
                        session.getSessionId(), target,
                        mfaProperties.getEmail().getCodeLength(),
                        mfaProperties.getEmail().getExpireMinutes());
                emailService.sendVerificationCode(target, code);
            }
            case TOTP -> {
                return AuthResponse.builder()
                        .sessionId(session.getSessionId())
                        .status(AuthStatus.IN_PROGRESS)
                        .message("请输入Google Authenticator中的6位验证码")
                        .requiredFactors(session.getRequiredFactors())
                        .completedFactors(session.getCompletedFactors())
                        .currentStep(session.getCompletedFactors().size() + 1)
                        .totalSteps(session.getRequiredFactors().size())
                        .build();
            }
            case BIOMETRIC_FINGERPRINT, BIOMETRIC_FACE -> {
                return AuthResponse.builder()
                        .sessionId(session.getSessionId())
                        .status(AuthStatus.IN_PROGRESS)
                        .message("请进行" + (factorType == FactorType.BIOMETRIC_FINGERPRINT ? "指纹" : "人脸") + "识别验证")
                        .requiredFactors(session.getRequiredFactors())
                        .completedFactors(session.getCompletedFactors())
                        .currentStep(session.getCompletedFactors().size() + 1)
                        .totalSteps(session.getRequiredFactors().size())
                        .build();
            }
            case WEBAUTHN -> {
                return AuthResponse.builder()
                        .sessionId(session.getSessionId())
                        .status(AuthStatus.IN_PROGRESS)
                        .message("请插入硬件密钥并触摸按钮进行验证")
                        .requiredFactors(session.getRequiredFactors())
                        .completedFactors(session.getCompletedFactors())
                        .currentStep(session.getCompletedFactors().size() + 1)
                        .totalSteps(session.getRequiredFactors().size())
                        .build();
            }
            default -> {
                return AuthResponse.builder()
                        .sessionId(session.getSessionId())
                        .status(AuthStatus.FAILED)
                        .message("不支持的认证因子类型")
                        .build();
            }
        }

        auditLogService.logAuthentication(session.getSessionId(), user, factorType,
                AuthStatus.IN_PROGRESS, "Verification code sent", httpRequest, session.getRiskAssessment());

        log.info("{} code sent for user: {}, session: {}", factorType, user.getUsername(), session.getSessionId());

        return AuthResponse.builder()
                .sessionId(session.getSessionId())
                .status(AuthStatus.IN_PROGRESS)
                .message("验证码已发送，请查收")
                .requiredFactors(session.getRequiredFactors())
                .completedFactors(session.getCompletedFactors())
                .currentStep(session.getCompletedFactors().size() + 1)
                .totalSteps(session.getRequiredFactors().size())
                .build();
    }

    @Override
    public AuthResponse verifyCode(VerifyCodeRequest request, HttpServletRequest httpRequest) {
        log.info("Verify code request for session: {}, factor: {}", request.getSessionId(), request.getFactorType());

        AuthSession session = authSessionService.getSession(request.getSessionId())
                .orElse(null);

        if (session == null) {
            return AuthResponse.builder()
                    .sessionId(request.getSessionId())
                    .status(AuthStatus.FAILED)
                    .message("会话不存在或已过期")
                    .build();
        }

        User user = session.getUser();
        FactorType factorType = request.getFactorType();

        if (session.isFactorCompleted(factorType)) {
            return checkAndCompleteAuthentication(session, httpRequest);
        }

        boolean valid = false;
        String errorMessage = null;

        if (factorType == FactorType.TOTP) {
            java.util.List<AuthFactor> totpFactors = authFactorRepository.findByUserIdAndFactorType(
                    user.getId(), FactorType.TOTP);
            if (totpFactors.isEmpty()) {
                errorMessage = "用户未配置TOTP";
            } else {
                AuthFactor totpFactor = totpFactors.stream()
                        .filter(f -> f.isVerified() && f.isEnabled())
                        .findFirst()
                        .orElse(null);
                if (totpFactor == null) {
                    errorMessage = "TOTP未验证或已禁用";
                } else {
                    TotpVerificationResult result = totpService.verifyCodeWithDrift(
                            totpFactor.getSecret(),
                            request.getCode(),
                            user.getId().toString()
                    );
                    valid = result.isValid();
                    if (!valid) {
                        errorMessage = "TOTP验证码错误，请检查时间是否同步";
                        log.warn("TOTP verification failed, drift offset tried: {}, server time: {}",
                                result.getDriftOffset(), result.getServerTime());
                    } else {
                        log.info("TOTP verified with drift offset: {} steps", result.getDriftOffset());
                    }
                }
            }
        } else {
            String target = switch (factorType) {
                case SMS -> user.getPhone();
                case EMAIL -> user.getEmail();
                default -> null;
            };

            if (target == null) {
                errorMessage = "用户未配置该认证方式";
            } else {
                valid = verificationCodeService.verifyCode(session.getSessionId(), target, request.getCode());
                if (!valid) {
                    errorMessage = "验证码错误或已过期";
                }
            }
        }

        if (!valid) {
            auditLogService.logAuthentication(session.getSessionId(), user, factorType,
                    AuthStatus.FAILED, errorMessage, httpRequest, session.getRiskAssessment());
            log.warn("Invalid {} code for user: {}", factorType, user.getUsername());
            return AuthResponse.builder()
                    .sessionId(session.getSessionId())
                    .status(AuthStatus.FAILED)
                    .message(errorMessage)
                    .requiredFactors(session.getRequiredFactors())
                    .completedFactors(session.getCompletedFactors())
                    .build();
        }

        session.addCompletedFactor(factorType);
        authSessionService.updateSession(session);

        auditLogService.logAuthentication(session.getSessionId(), user, factorType,
                AuthStatus.SUCCESS, "Code verified successfully", httpRequest, session.getRiskAssessment());

        log.info("{} code verified for user: {}", factorType, user.getUsername());

        return checkAndCompleteAuthentication(session, httpRequest);
    }

    @Override
    public AuthResponse verifyWebAuthn(String sessionId, WebAuthnAssertion assertion, HttpServletRequest httpRequest) {
        log.info("WebAuthn verification request for session: {}", sessionId);

        AuthSession session = authSessionService.getSession(sessionId)
                .orElse(null);

        if (session == null) {
            return AuthResponse.builder()
                    .sessionId(sessionId)
                    .status(AuthStatus.FAILED)
                    .message("会话不存在或已过期")
                    .build();
        }

        User user = session.getUser();

        if (session.isFactorCompleted(FactorType.WEBAUTHN)) {
            return checkAndCompleteAuthentication(session, httpRequest);
        }

        boolean verified = webAuthnService.verifyAuthentication(sessionId, assertion, user);

        if (!verified) {
            auditLogService.logAuthentication(session.getSessionId(), user, FactorType.WEBAUTHN,
                    AuthStatus.FAILED, "WebAuthn verification failed", httpRequest, session.getRiskAssessment());
            return AuthResponse.builder()
                    .sessionId(session.getSessionId())
                    .status(AuthStatus.FAILED)
                    .message("WebAuthn验证失败")
                    .requiredFactors(session.getRequiredFactors())
                    .completedFactors(session.getCompletedFactors())
                    .build();
        }

        session.addCompletedFactor(FactorType.WEBAUTHN);
        authSessionService.updateSession(session);

        auditLogService.logAuthentication(session.getSessionId(), user, FactorType.WEBAUTHN,
                AuthStatus.SUCCESS, "WebAuthn verified successfully", httpRequest, session.getRiskAssessment());

        log.info("WebAuthn verified for user: {}", user.getUsername());

        return checkAndCompleteAuthentication(session, httpRequest);
    }

    @Override
    public AuthResponse verifyBiometric(String sessionId, FactorType factorType, String biometricData, HttpServletRequest httpRequest) {
        log.info("Biometric verification request for session: {}, type: {}", sessionId, factorType);

        AuthSession session = authSessionService.getSession(sessionId)
                .orElse(null);

        if (session == null) {
            return AuthResponse.builder()
                    .sessionId(sessionId)
                    .status(AuthStatus.FAILED)
                    .message("会话不存在或已过期")
                    .build();
        }

        User user = session.getUser();

        if (session.isFactorCompleted(factorType)) {
            return checkAndCompleteAuthentication(session, httpRequest);
        }

        boolean verified = biometricService.verifyBiometric(sessionId, user, factorType, biometricData);

        if (!verified) {
            auditLogService.logAuthentication(session.getSessionId(), user, factorType,
                    AuthStatus.FAILED, "Biometric verification failed", httpRequest, session.getRiskAssessment());
            return AuthResponse.builder()
                    .sessionId(session.getSessionId())
                    .status(AuthStatus.FAILED)
                    .message("生物识别验证失败")
                    .requiredFactors(session.getRequiredFactors())
                    .completedFactors(session.getCompletedFactors())
                    .build();
        }

        session.addCompletedFactor(factorType);
        authSessionService.updateSession(session);

        auditLogService.logAuthentication(session.getSessionId(), user, factorType,
                AuthStatus.SUCCESS, "Biometric verified successfully", httpRequest, session.getRiskAssessment());

        log.info("{} verified for user: {}", factorType, user.getUsername());

        return checkAndCompleteAuthentication(session, httpRequest);
    }

    @Override
    public AuthResponse getAuthStatus(String sessionId) {
        AuthSession session = authSessionService.getSession(sessionId)
                .orElse(null);

        if (session == null) {
            return AuthResponse.builder()
                    .sessionId(sessionId)
                    .status(AuthStatus.EXPIRED)
                    .message("会话不存在或已过期")
                    .build();
        }

        return buildAuthResponse(session);
    }

    @Override
    @Transactional
    public AuthResponse registerFactor(User user, FactorType factorType, String name) {
        AuthFactor factor = new AuthFactor();
        factor.setUser(user);
        factor.setFactorType(factorType);
        factor.setName(name != null ? name : factorType.name());
        factor.setEnabled(true);
        factor.setVerified(false);

        authFactorRepository.save(factor);

        return AuthResponse.builder()
                .message("认证因子注册成功，请完成验证")
                .build();
    }

    @Override
    public void logout(String sessionId) {
        authSessionService.invalidateSession(sessionId);
        log.info("User logged out, session: {}", sessionId);
    }

    private AuthResponse checkAndCompleteAuthentication(AuthSession session, HttpServletRequest httpRequest) {
        boolean policySatisfied = authPolicyService.isPolicySatisfied(
                session.getUser(),
                session.getCompletedFactors(),
                session.getRiskAssessment());

        String authLevel = adaptiveAuthService.getAuthenticationLevel(session.getRiskAssessment());
        RiskAssessment riskAssessment = session.getRiskAssessment();

        if (policySatisfied) {
            session.setStatus(AuthStatus.SUCCESS);
            authSessionService.updateSession(session);

            auditLogService.logAuthentication(session.getSessionId(), session.getUser(), null,
                    AuthStatus.SUCCESS,
                    String.format("All MFA factors verified, authentication complete (level: %s)", authLevel),
                    httpRequest, riskAssessment);

            String token = jwtService.generateToken(session.getUser());
            authSessionService.invalidateSession(session.getSessionId());

            log.info("Authentication complete for user: {}, level: {}",
                    session.getUser().getUsername(), authLevel);

            return AuthResponse.builder()
                    .sessionId(session.getSessionId())
                    .status(AuthStatus.SUCCESS)
                    .message("认证成功")
                    .token(token)
                    .completedFactors(session.getCompletedFactors())
                    .requiredFactors(session.getRequiredFactors())
                    .mfaRequired(true)
                    .currentStep(session.getCompletedFactors().size())
                    .totalSteps(session.getRequiredFactors().size())
                    .riskScore(riskAssessment.getScore())
                    .riskLevel(riskAssessment.getLevel())
                    .adaptiveAuthLevel(authLevel)
                    .build();
        }

        return buildAuthResponse(session, authLevel);
    }

    private AuthResponse buildAuthResponse(AuthSession session) {
        String authLevel = adaptiveAuthService.getAuthenticationLevel(session.getRiskAssessment());
        return buildAuthResponse(session, authLevel);
    }

    private AuthResponse buildAuthResponse(AuthSession session, String authLevel) {
        List<FactorType> availableFactors = authFactorRepository.findVerifiedFactorTypesByUserId(
                session.getUser().getId());

        RiskAssessment riskAssessment = session.getRiskAssessment();
        boolean stepUpRequired = adaptiveAuthService.shouldStepUpAuthentication(
                session.getUser(), riskAssessment, session.getCompletedFactors().size());

        String message = "请完成多因素认证";
        if (stepUpRequired) {
            message = "检测到高风险操作，需要额外验证";
        } else if ("SIMPLIFIED".equals(authLevel)) {
            message = "低风险场景，简化认证流程";
        }

        return AuthResponse.builder()
                .sessionId(session.getSessionId())
                .status(session.getStatus())
                .message(message)
                .requiredFactors(session.getRequiredFactors())
                .completedFactors(session.getCompletedFactors())
                .availableFactors(availableFactors)
                .mfaRequired(true)
                .currentStep(session.getCompletedFactors().size() + 1)
                .totalSteps(session.getRequiredFactors().size())
                .riskScore(riskAssessment.getScore())
                .riskLevel(riskAssessment.getLevel())
                .adaptiveAuthLevel(authLevel)
                .stepUpRequired(stepUpRequired)
                .build();
    }

    @Override
    public WebAuthnOptionsResponse getPasskeyAuthenticationOptions(String sessionId) {
        return webAuthnService.generatePasskeyAuthenticationOptions(sessionId);
    }

    @Override
    public AuthResponse loginWithPasskey(String sessionId, WebAuthnAssertion assertion, HttpServletRequest httpRequest) {
        log.info("Passkey login attempt for session: {}", sessionId);

        User user = webAuthnService.verifyPasskeyAuthentication(sessionId, assertion);
        if (user == null) {
            auditLogService.logAuthentication(sessionId, null, FactorType.WEBAUTHN,
                    AuthStatus.FAILED, "Passkey authentication failed", httpRequest, null);
            log.warn("Passkey authentication failed for session: {}", sessionId);
            return AuthResponse.builder()
                    .sessionId(sessionId)
                    .status(AuthStatus.FAILED)
                    .message("Passkey验证失败，请重试或使用其他登录方式")
                    .build();
        }

        if (!user.isEnabled() || user.isAccountLocked()) {
            auditLogService.logAuthentication(sessionId, user, FactorType.WEBAUTHN,
                    AuthStatus.FAILED, "Account disabled or locked", httpRequest, null);
            return AuthResponse.builder()
                    .sessionId(sessionId)
                    .status(AuthStatus.FAILED)
                    .message("账号已被禁用或锁定")
                    .build();
        }

        RiskAssessment riskAssessment = riskAssessmentService.assessRisk(user, httpRequest);
        AuthSession authSession = authSessionService.createSession(user, riskAssessment);

        String authMethod = "WEBAUTHN_PASSKEY";
        if (assertion.getResponse() != null && assertion.getResponse().getAuthenticatorData() != null) {
            authMethod = "PASSKEY_BIOMETRIC";
        }

        authSession.addCompletedFactor(FactorType.WEBAUTHN);
        authSession.setStatus(AuthStatus.SUCCESS);
        authSessionService.updateSession(authSession);

        auditLogService.logAuthentication(sessionId, user, FactorType.WEBAUTHN,
                AuthStatus.SUCCESS, "Passkey authentication successful",
                httpRequest, riskAssessment);

        String token = jwtService.generateToken(user);
        authSessionService.invalidateSession(authSession.getSessionId());

        log.info("Passkey login successful for user: {}, method: {}", user.getUsername(), authMethod);

        return AuthResponse.builder()
                .sessionId(sessionId)
                .status(AuthStatus.SUCCESS)
                .message("Passkey登录成功")
                .token(token)
                .completedFactors(java.util.Collections.singletonList(FactorType.WEBAUTHN))
                .requiredFactors(java.util.Collections.emptyList())
                .mfaRequired(false)
                .currentStep(1)
                .totalSteps(1)
                .riskScore(riskAssessment.getScore())
                .riskLevel(riskAssessment.getLevel())
                .build();
    }

    @Override
    public WebAuthnOptionsResponse getPasskeyRegistrationOptions(String sessionId, User user) {
        return webAuthnService.generatePasskeyRegistrationOptions(sessionId, user);
    }
}
