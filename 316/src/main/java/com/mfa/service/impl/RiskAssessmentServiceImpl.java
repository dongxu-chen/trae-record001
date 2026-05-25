package com.mfa.service.impl;

import com.mfa.config.MfaProperties;
import com.mfa.dto.BehavioralBiometrics;
import com.mfa.dto.RiskAssessment;
import com.mfa.entity.User;
import com.mfa.enums.AuthStatus;
import com.mfa.enums.RiskLevel;
import com.mfa.repository.AuthLogRepository;
import com.mfa.service.BehavioralBiometricsService;
import com.mfa.service.RiskAssessmentService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class RiskAssessmentServiceImpl implements RiskAssessmentService {

    private final AuthLogRepository authLogRepository;
    private final MfaProperties mfaProperties;
    private final BehavioralBiometricsService behavioralBiometricsService;
    private final RedisTemplate<String, Object> redisTemplate;

    private static final String BEHAVIORAL_ANALYSIS_KEY_PREFIX = "mfa:behavior:analysis:";
    private static final int RISK_NEW_IP = 15;
    private static final int RISK_NEW_DEVICE = 15;
    private static final int RISK_UNUSUAL_HOUR = 10;
    private static final int RISK_HIGH_FAILURE_RATE = 25;
    private static final int RISK_FREQUENT_LOGINS = 15;
    private static final int RISK_NEW_LOCATION = 20;
    private static final int RISK_VPN_DETECTED = 20;
    private static final int RISK_TOR_DETECTED = 30;
    private static final int RISK_BEHAVIOR_ANOMALY_MAX = 40;

    @Override
    public RiskAssessment assessRisk(User user, HttpServletRequest request) {
        int totalScore = 0;
        List<String> riskFactors = new ArrayList<>();
        Map<String, Object> details = new HashMap<>();

        String ipAddress = getClientIp(request);
        String userAgent = request.getHeader("User-Agent");
        String deviceFingerprint = generateDeviceFingerprint(request);

        log.debug("Assessing risk for user: {}, IP: {}", user.getUsername(), ipAddress);

        if (isNewIpAddress(user.getId(), ipAddress)) {
            totalScore += RISK_NEW_IP;
            riskFactors.add("NEW_IP_ADDRESS");
            details.put("newIpAddress", ipAddress);
        }

        if (isNewDevice(user.getId(), deviceFingerprint)) {
            totalScore += RISK_NEW_DEVICE;
            riskFactors.add("NEW_DEVICE");
            details.put("newDevice", true);
        }

        if (isUnusualHour()) {
            totalScore += RISK_UNUSUAL_HOUR;
            riskFactors.add("UNUSUAL_LOGIN_HOUR");
            details.put("unusualHour", LocalDateTime.now().getHour());
        }

        int failureRateScore = calculateFailureRateRisk(user.getId());
        if (failureRateScore > 0) {
            totalScore += failureRateScore;
            riskFactors.add("HIGH_FAILURE_RATE");
            details.put("failureRateScore", failureRateScore);
        }

        int frequentLoginScore = calculateFrequentLoginRisk(user.getId());
        if (frequentLoginScore > 0) {
            totalScore += frequentLoginScore;
            riskFactors.add("FREQUENT_LOGINS");
            details.put("frequentLoginScore", frequentLoginScore);
        }

        if (isVpnOrProxy(ipAddress)) {
            totalScore += RISK_VPN_DETECTED;
            riskFactors.add("VPN_PROXY_DETECTED");
            details.put("vpnDetected", true);
        }

        int behaviorRiskScore = calculateBehaviorRisk(user.getId().toString());
        if (behaviorRiskScore > 0) {
            totalScore += behaviorRiskScore;
            riskFactors.add("BEHAVIORAL_ANOMALY_DETECTED");
            details.put("behaviorRiskScore", behaviorRiskScore);
        }

        totalScore = Math.min(totalScore, mfaProperties.getRisk().getMaxRiskScore());

        RiskLevel riskLevel = determineRiskLevel(totalScore);
        boolean stepUpRequired = totalScore >= mfaProperties.getRisk().getThresholdHigh();

        log.debug("Risk assessment completed for user: {}, score: {}, level: {}",
                user.getUsername(), totalScore, riskLevel);

        return RiskAssessment.builder()
                .score(totalScore)
                .level(riskLevel.name())
                .riskFactors(riskFactors)
                .details(details)
                .stepUpRequired(stepUpRequired)
                .build();
    }

    private int calculateBehaviorRisk(String userId) {
        try {
            String key = BEHAVIORAL_ANALYSIS_KEY_PREFIX + "latest:" + userId;
            Object obj = redisTemplate.opsForValue().get(key);
            if (obj == null) {
                return 0;
            }

            BehavioralBiometrics latestAnalysis = null;
            if (obj instanceof BehavioralBiometrics) {
                latestAnalysis = (BehavioralBiometrics) obj;
            } else if (obj instanceof java.util.LinkedHashMap) {
                com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
                latestAnalysis = mapper.convertValue(obj, BehavioralBiometrics.class);
            }

            if (latestAnalysis == null || latestAnalysis.getRiskScore() == null) {
                return 0;
            }

            if (latestAnalysis.getTimestamp() != null
                    && latestAnalysis.getTimestamp().isBefore(LocalDateTime.now().minusMinutes(30))) {
                return 0;
            }

            int behaviorScore = latestAnalysis.getRiskScore();
            if (behaviorScore > 0) {
                log.debug("Behavioral risk detected for user: {}, score: {}", userId, behaviorScore);
            }
            return Math.min(behaviorScore, RISK_BEHAVIOR_ANOMALY_MAX);

        } catch (Exception e) {
            log.warn("Failed to calculate behavior risk", e);
            return 0;
        }
    }

    private boolean isNewIpAddress(Long userId, String ipAddress) {
        LocalDateTime oneMonthAgo = LocalDateTime.now().minusMonths(1);
        long distinctIps = authLogRepository.countDistinctIpAddressesByUserIdAndCreatedAtAfter(
                userId, oneMonthAgo);

        if (distinctIps == 0) {
            return false;
        }

        List<String> recentIps = authLogRepository.findByUserIdOrderByCreatedAtDesc(userId)
                .stream()
                .limit(50)
                .map(log -> log.getIpAddress())
                .filter(Objects::nonNull)
                .distinct()
                .toList();

        return !recentIps.contains(ipAddress);
    }

    private boolean isNewDevice(Long userId, String deviceFingerprint) {
        List<String> recentDevices = authLogRepository.findByUserIdOrderByCreatedAtDesc(userId)
                .stream()
                .limit(50)
                .map(log -> log.getDeviceFingerprint())
                .filter(Objects::nonNull)
                .distinct()
                .toList();

        return !recentDevices.isEmpty() && !recentDevices.contains(deviceFingerprint);
    }

    private boolean isUnusualHour() {
        int hour = LocalDateTime.now().getHour();
        return hour >= 1 && hour < 6;
    }

    private int calculateFailureRateRisk(Long userId) {
        LocalDateTime lastHour = LocalDateTime.now().minusHours(1);
        long failures = authLogRepository.countByUserIdAndStatusAndCreatedAtAfter(
                userId, AuthStatus.FAILED, lastHour);
        long successes = authLogRepository.countByUserIdAndStatusAndCreatedAtAfter(
                userId, AuthStatus.SUCCESS, lastHour);

        long total = failures + successes;
        if (total == 0) {
            return 0;
        }

        double failureRate = (double) failures / total;

        if (failureRate > 0.5 && failures >= 3) {
            return RISK_HIGH_FAILURE_RATE;
        } else if (failureRate > 0.3 && failures >= 2) {
            return RISK_HIGH_FAILURE_RATE / 2;
        }

        return 0;
    }

    private int calculateFrequentLoginRisk(Long userId) {
        LocalDateTime last15Minutes = LocalDateTime.now().minusMinutes(15);
        long attempts = authLogRepository.countByUserIdAndStatusAndCreatedAtAfter(
                userId, AuthStatus.FAILED, last15Minutes) +
                authLogRepository.countByUserIdAndStatusAndCreatedAtAfter(
                        userId, AuthStatus.SUCCESS, last15Minutes);

        if (attempts > 10) {
            return RISK_FREQUENT_LOGINS;
        } else if (attempts > 5) {
            return RISK_FREQUENT_LOGINS / 2;
        }

        return 0;
    }

    private boolean isVpnOrProxy(String ipAddress) {
        return false;
    }

    private RiskLevel determineRiskLevel(int score) {
        if (score >= mfaProperties.getRisk().getThresholdHigh()) {
            return RiskLevel.HIGH;
        } else if (score >= mfaProperties.getRisk().getThresholdMedium()) {
            return RiskLevel.MEDIUM;
        }
        return RiskLevel.LOW;
    }

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        String xRealIp = request.getHeader("X-Real-IP");
        if (xRealIp != null && !xRealIp.isEmpty()) {
            return xRealIp;
        }
        return request.getRemoteAddr();
    }

    private String generateDeviceFingerprint(HttpServletRequest request) {
        String userAgent = request.getHeader("User-Agent");
        String acceptLanguage = request.getHeader("Accept-Language");
        String acceptEncoding = request.getHeader("Accept-Encoding");

        String raw = userAgent + "|" + acceptLanguage + "|" + acceptEncoding;
        return Base64.getEncoder().encodeToString(Objects.requireNonNullElse(raw, "").getBytes());
    }
}
