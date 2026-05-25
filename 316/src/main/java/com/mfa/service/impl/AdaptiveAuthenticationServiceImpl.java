package com.mfa.service.impl;

import com.mfa.config.MfaProperties;
import com.mfa.dto.RiskAssessment;
import com.mfa.entity.AuthFactor;
import com.mfa.entity.AuthPolicy;
import com.mfa.entity.User;
import com.mfa.enums.FactorType;
import com.mfa.enums.RiskLevel;
import com.mfa.repository.AuthFactorRepository;
import com.mfa.service.AdaptiveAuthenticationService;
import com.mfa.service.AuthPolicyService;
import com.mfa.service.RiskAssessmentService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class AdaptiveAuthenticationServiceImpl implements AdaptiveAuthenticationService {

    private final RiskAssessmentService riskAssessmentService;
    private final AuthPolicyService authPolicyService;
    private final AuthFactorRepository authFactorRepository;
    private final StringRedisTemplate redisTemplate;
    private final MfaProperties mfaProperties;

    private static final String TRUSTED_DEVICE_PREFIX = "trusted_device:";
    private static final String DEVICE_HISTORY_PREFIX = "device_history:";
    private static final String USER_LOCATION_PREFIX = "user_location:";

    @Override
    public RiskAssessment assessAdaptiveRisk(User user, HttpServletRequest request) {
        RiskAssessment baseAssessment = riskAssessmentService.assessRisk(user, request);

        List<String> adaptiveFactors = new ArrayList<>(baseAssessment.getRiskFactors());
        Map<String, Object> details = new HashMap<>(baseAssessment.getDetails());

        boolean isTrustedDevice = isTrustedDevice(user, request);
        if (isTrustedDevice) {
            baseAssessment.setScore(Math.max(0, baseAssessment.getScore() - 20));
            adaptiveFactors.add("TRUSTED_DEVICE");
            details.put("trustedDevice", true);
        } else {
            details.put("trustedDevice", false);
        }

        boolean isKnownLocation = isKnownLocation(user, request);
        if (isKnownLocation) {
            baseAssessment.setScore(Math.max(0, baseAssessment.getScore() - 10));
            adaptiveFactors.add("KNOWN_LOCATION");
            details.put("knownLocation", true);
        } else {
            details.put("knownLocation", false);
        }

        boolean isOffHours = isOffHours();
        if (isOffHours) {
            baseAssessment.setScore(Math.min(100, baseAssessment.getScore() + 10));
            adaptiveFactors.add("OFF_HOURS_ACCESS");
            details.put("offHours", true);
        } else {
            details.put("offHours", false);
        }

        int recentFailures = getRecentFailureCount(user, request);
        if (recentFailures > 0) {
            int penalty = Math.min(30, recentFailures * 5);
            baseAssessment.setScore(Math.min(100, baseAssessment.getScore() + penalty));
            adaptiveFactors.add("RECENT_FAILURES:" + recentFailures);
            details.put("recentFailures", recentFailures);
        }

        RiskLevel riskLevel = determineRiskLevel(baseAssessment.getScore());
        baseAssessment.setLevel(riskLevel.name());
        baseAssessment.setRiskFactors(adaptiveFactors);
        baseAssessment.setDetails(details);

        boolean stepUpRequired = shouldStepUpAuthentication(user, baseAssessment, 0);
        baseAssessment.setStepUpRequired(stepUpRequired);

        log.debug("Adaptive risk assessment for user {}: score={}, level={}, factors={}",
                user.getUsername(), baseAssessment.getScore(), baseAssessment.getLevel(), adaptiveFactors);

        return baseAssessment;
    }

    @Override
    public List<FactorType> determineAdaptiveRequiredFactors(User user, RiskAssessment riskAssessment) {
        AuthPolicy policy = authPolicyService.getUserPolicy(user);
        List<FactorType> userAvailableFactors = authFactorRepository.findVerifiedFactorTypesByUserId(user.getId());

        if (shouldBypassMfa(user, null, riskAssessment)) {
            log.info("Bypassing MFA for user {} due to low risk and trusted device", user.getUsername());
            return Collections.emptyList();
        }

        List<FactorType> baseFactors = authPolicyService.determineRequiredFactors(user, riskAssessment);
        RiskLevel riskLevel = RiskLevel.valueOf(riskAssessment.getLevel());

        List<FactorType> adaptiveFactors = new ArrayList<>();

        switch (riskLevel) {
            case LOW:
                adaptiveFactors = selectPreferredFactors(baseFactors, userAvailableFactors, Arrays.asList(
                        FactorType.WEBAUTHN,
                        FactorType.FINGERPRINT,
                        FactorType.FACE,
                        FactorType.TOTP,
                        FactorType.SMS,
                        FactorType.EMAIL
                ));
                break;

            case MEDIUM:
                adaptiveFactors = selectPreferredFactors(baseFactors, userAvailableFactors, Arrays.asList(
                        FactorType.TOTP,
                        FactorType.WEBAUTHN,
                        FactorType.FINGERPRINT,
                        FactorType.FACE,
                        FactorType.SMS,
                        FactorType.EMAIL
                ));
                break;

            case HIGH:
                adaptiveFactors = selectPreferredFactors(baseFactors, userAvailableFactors, Arrays.asList(
                        FactorType.TOTP,
                        FactorType.WEBAUTHN,
                        FactorType.SMS,
                        FactorType.EMAIL,
                        FactorType.FINGERPRINT,
                        FactorType.FACE
                ));

                if (adaptiveFactors.size() < 2 && userAvailableFactors.contains(FactorType.SMS)) {
                    if (!adaptiveFactors.contains(FactorType.SMS)) {
                        adaptiveFactors.add(FactorType.SMS);
                    }
                }
                break;

            case CRITICAL:
                adaptiveFactors = new ArrayList<>();

                if (userAvailableFactors.contains(FactorType.TOTP)) {
                    adaptiveFactors.add(FactorType.TOTP);
                }
                if (userAvailableFactors.contains(FactorType.SMS) && !adaptiveFactors.contains(FactorType.SMS)) {
                    adaptiveFactors.add(FactorType.SMS);
                }
                if (userAvailableFactors.contains(FactorType.WEBAUTHN) && adaptiveFactors.size() < 3) {
                    adaptiveFactors.add(FactorType.WEBAUTHN);
                }

                if (adaptiveFactors.size() < 2) {
                    for (FactorType type : userAvailableFactors) {
                        if (!adaptiveFactors.contains(type)) {
                            adaptiveFactors.add(type);
                            if (adaptiveFactors.size() >= 3) break;
                        }
                    }
                }
                break;
        }

        int requiredCount = authPolicyService.getRequiredFactorCount(policy, riskAssessment);
        if (adaptiveFactors.size() > requiredCount) {
            adaptiveFactors = adaptiveFactors.subList(0, requiredCount);
        }

        log.debug("Adaptive required factors for user {} (risk: {}): {}",
                user.getUsername(), riskLevel, adaptiveFactors);

        return adaptiveFactors;
    }

    @Override
    public boolean shouldBypassMfa(User user, HttpServletRequest request, RiskAssessment riskAssessment) {
        if (riskAssessment == null) {
            return false;
        }

        RiskLevel riskLevel = RiskLevel.valueOf(riskAssessment.getLevel());

        if (riskLevel != RiskLevel.LOW) {
            return false;
        }

        AuthPolicy policy = authPolicyService.getUserPolicy(user);
        if (!policy.isAdaptiveEnabled()) {
            return false;
        }

        if (request != null && isTrustedDevice(user, request)) {
            Boolean bypassEnabled = mfaProperties.getAdaptive().isTrustedDeviceBypassEnabled();
            if (bypassEnabled != null && bypassEnabled) {
                log.info("MFA bypassed for trusted device of user {}", user.getUsername());
                return true;
            }
        }

        return false;
    }

    @Override
    public boolean shouldStepUpAuthentication(User user, RiskAssessment currentRisk, int completedFactors) {
        if (currentRisk == null) {
            return false;
        }

        RiskLevel riskLevel = RiskLevel.valueOf(currentRisk.getLevel());
        AuthPolicy policy = authPolicyService.getUserPolicy(user);

        if (!policy.isStepUpEnabled()) {
            return false;
        }

        int requiredCount = authPolicyService.getRequiredFactorCount(policy, currentRisk);

        return completedFactors < requiredCount &&
                (riskLevel == RiskLevel.HIGH || riskLevel == RiskLevel.CRITICAL);
    }

    @Override
    public String getAuthenticationLevel(RiskAssessment riskAssessment) {
        if (riskAssessment == null) {
            return "STANDARD";
        }

        RiskLevel riskLevel = RiskLevel.valueOf(riskAssessment.getLevel());

        return switch (riskLevel) {
            case LOW -> "SIMPLIFIED";
            case MEDIUM -> "STANDARD";
            case HIGH -> "ELEVATED";
            case CRITICAL -> "MAXIMUM";
        };
    }

    @Override
    public boolean isTrustedDevice(User user, HttpServletRequest request) {
        if (request == null || user == null) {
            return false;
        }

        String deviceFingerprint = getDeviceFingerprint(request);
        if (deviceFingerprint == null) {
            return false;
        }

        String key = TRUSTED_DEVICE_PREFIX + user.getId() + ":" + deviceFingerprint;
        Boolean isTrusted = redisTemplate.hasKey(key);

        return Boolean.TRUE.equals(isTrusted);
    }

    @Override
    public void markDeviceAsTrusted(User user, HttpServletRequest request, int days) {
        if (request == null || user == null) {
            return;
        }

        String deviceFingerprint = getDeviceFingerprint(request);
        if (deviceFingerprint == null) {
            return;
        }

        String key = TRUSTED_DEVICE_PREFIX + user.getId() + ":" + deviceFingerprint;
        redisTemplate.opsForValue().set(key, "trusted", days, TimeUnit.DAYS);

        String historyKey = DEVICE_HISTORY_PREFIX + user.getId();
        redisTemplate.opsForSet().add(historyKey, deviceFingerprint);
        redisTemplate.expire(historyKey, 365, TimeUnit.DAYS);

        log.info("Device marked as trusted for user {} for {} days", user.getUsername(), days);
    }

    private List<FactorType> selectPreferredFactors(
            List<FactorType> baseFactors,
            List<FactorType> availableFactors,
            List<FactorType> preferenceOrder) {

        List<FactorType> result = new ArrayList<>();

        for (FactorType preferred : preferenceOrder) {
            if (baseFactors.contains(preferred) && availableFactors.contains(preferred)) {
                result.add(preferred);
            }
        }

        for (FactorType factor : baseFactors) {
            if (!result.contains(factor) && availableFactors.contains(factor)) {
                result.add(factor);
            }
        }

        return result;
    }

    private RiskLevel determineRiskLevel(int score) {
        if (score < 30) return RiskLevel.LOW;
        if (score < 50) return RiskLevel.MEDIUM;
        if (score < 75) return RiskLevel.HIGH;
        return RiskLevel.CRITICAL;
    }

    private String getDeviceFingerprint(HttpServletRequest request) {
        String fingerprint = request.getHeader("X-Device-Fingerprint");
        if (fingerprint != null && !fingerprint.isEmpty()) {
            return fingerprint;
        }

        String userAgent = request.getHeader("User-Agent");
        String acceptLanguage = request.getHeader("Accept-Language");
        if (userAgent != null) {
            return String.valueOf((userAgent + "|" + acceptLanguage).hashCode());
        }

        return null;
    }

    private boolean isKnownLocation(User user, HttpServletRequest request) {
        String ipAddress = getClientIp(request);
        if (ipAddress == null || user == null) {
            return false;
        }

        String key = USER_LOCATION_PREFIX + user.getId();
        Set<String> knownIps = redisTemplate.opsForSet().members(key);

        if (knownIps != null && knownIps.contains(ipAddress)) {
            return true;
        }

        if (knownIps != null && !knownIps.isEmpty()) {
            for (String knownIp : knownIps) {
                if (isSameSubnet(knownIp, ipAddress)) {
                    return true;
                }
            }
        }

        return false;
    }

    private boolean isSameSubnet(String ip1, String ip2) {
        try {
            String[] parts1 = ip1.split("\\.");
            String[] parts2 = ip2.split("\\.");
            if (parts1.length >= 3 && parts2.length >= 3) {
                return parts1[0].equals(parts2[0]) &&
                        parts1[1].equals(parts2[1]) &&
                        parts1[2].equals(parts2[2]);
            }
        } catch (Exception e) {
            log.debug("Failed to compare IP subnets", e);
        }
        return false;
    }

    private boolean isOffHours() {
        Calendar calendar = Calendar.getInstance();
        int hour = calendar.get(Calendar.HOUR_OF_DAY);
        int dayOfWeek = calendar.get(Calendar.DAY_OF_WEEK);

        boolean isWeekend = (dayOfWeek == Calendar.SATURDAY || dayOfWeek == Calendar.SUNDAY);
        boolean isOffHour = (hour < 8 || hour > 22);

        return isWeekend || isOffHour;
    }

    private int getRecentFailureCount(User user, HttpServletRequest request) {
        if (user == null) return 0;

        String key = "auth_failures:" + user.getId();
        String countStr = redisTemplate.opsForValue().get(key);

        try {
            return countStr != null ? Integer.parseInt(countStr) : 0;
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String[] headers = {
                "X-Forwarded-For",
                "X-Real-IP",
                "Proxy-Client-IP",
                "WL-Proxy-Client-IP",
                "HTTP_X_FORWARDED_FOR",
                "HTTP_X_FORWARDED",
                "HTTP_X_CLUSTER_CLIENT_IP",
                "HTTP_CLIENT_IP",
                "HTTP_FORWARDED_FOR",
                "HTTP_FORWARDED"
        };

        for (String header : headers) {
            String ip = request.getHeader(header);
            if (ip != null && !ip.isEmpty() && !"unknown".equalsIgnoreCase(ip)) {
                int commaIndex = ip.indexOf(',');
                if (commaIndex != -1) {
                    return ip.substring(0, commaIndex).trim();
                }
                return ip;
            }
        }

        return request.getRemoteAddr();
    }
}
