package com.sso.service;

import com.sso.entity.User;
import com.sso.entity.UserLoginHistory;
import com.sso.repository.UserLoginHistoryRepository;
import com.sso.repository.UserRepository;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;

@Slf4j
@Service
@RequiredArgsConstructor
public class RiskAssessmentService {

    private static final int MAX_LOGIN_HISTORY = 10;
    private static final int TRUSTED_DEVICE_THRESHOLD = 3;

    private final UserRepository userRepository;
    private final UserLoginHistoryRepository loginHistoryRepository;

    public RiskAssessmentResult assessLoginRisk(String username, HttpServletRequest request) {
        User user = userRepository.findByUsername(username).orElse(null);
        if (user == null) {
            return RiskAssessmentResult.lowRisk("User not found");
        }

        String ipAddress = getClientIpAddress(request);
        String userAgent = request.getHeader("User-Agent");
        String deviceInfo = extractDeviceInfo(userAgent);

        RiskAssessmentResult result = new RiskAssessmentResult();
        result.setUsername(username);
        result.setIpAddress(ipAddress);
        result.setUserAgent(userAgent);
        result.setDeviceInfo(deviceInfo);

        List<UserLoginHistory> recentLogins = loginHistoryRepository
                .findByUsernameOrderByLoginTimeDesc(username);

        int riskScore = 0;

        boolean isNewLocation = checkNewLocation(username, ipAddress, recentLogins);
        boolean isNewDevice = checkNewDevice(username, deviceInfo, recentLogins);
        boolean isAbnormalTime = checkAbnormalLoginTime();
        boolean isSuspiciousIp = checkSuspiciousIp(ipAddress);

        if (isNewLocation) {
            result.addWarning("Login from new location: " + ipAddress);
            riskScore += 2;
        }

        if (isNewDevice) {
            result.addWarning("Login from new device: " + deviceInfo);
            riskScore += 2;
        }

        if (isAbnormalTime) {
            result.addWarning("Login during abnormal hours");
            riskScore += 1;
        }

        if (isSuspiciousIp) {
            result.addWarning("Login from suspicious IP range");
            riskScore += 3;
        }

        if (riskScore >= 5) {
            result.setRiskLevel(RiskLevel.HIGH);
            result.setRequireAdditionalVerification(true);
            result.setMessage("High risk login detected. Additional verification required.");
        } else if (riskScore >= 2) {
            result.setRiskLevel(RiskLevel.MEDIUM);
            result.setMessage("Medium risk login detected.");
        } else {
            result.setRiskLevel(RiskLevel.LOW);
            result.setMessage("Low risk login.");
        }

        result.setRiskScore(riskScore);

        saveLoginHistory(user, ipAddress, deviceInfo, userAgent, result);

        log.info("Risk assessment for user {}: score={}, level={}, warnings={}", 
                username, riskScore, result.getRiskLevel(), result.getWarnings());

        return result;
    }

    private boolean checkNewLocation(String username, String ipAddress, List<UserLoginHistory> recentLogins) {
        if (recentLogins.isEmpty()) {
            return false;
        }

        Set<String> knownIps = new java.util.HashSet<>();
        for (UserLoginHistory history : recentLogins) {
            if (history.getIpAddress() != null) {
                knownIps.add(history.getIpAddress());
            }
        }

        return !knownIps.contains(ipAddress);
    }

    private boolean checkNewDevice(String username, String deviceInfo, List<UserLoginHistory> recentLogins) {
        if (recentLogins.isEmpty()) {
            return false;
        }

        long trustedDeviceCount = recentLogins.stream()
                .filter(h -> deviceInfo.equals(h.getDeviceInfo()))
                .count();

        return trustedDeviceCount < TRUSTED_DEVICE_THRESHOLD;
    }

    private boolean checkAbnormalLoginTime() {
        LocalDateTime now = LocalDateTime.now();
        int hour = now.getHour();
        return hour < 2 || hour > 23;
    }

    private boolean checkSuspiciousIp(String ipAddress) {
        String[] parts = ipAddress.split("\\.");
        if (parts.length != 4) {
            return false;
        }

        try {
            int firstOctet = Integer.parseInt(parts[0]);
            if (firstOctet == 10 || firstOctet == 127) {
                return false;
            }
            if (firstOctet == 172 && Integer.parseInt(parts[1]) >= 16 && Integer.parseInt(parts[1]) <= 31) {
                return false;
            }
            if (firstOctet == 192 && Integer.parseInt(parts[1]) == 168) {
                return false;
            }
        } catch (NumberFormatException e) {
            return true;
        }

        return false;
    }

    private String getClientIpAddress(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }
        return ip != null ? ip : "unknown";
    }

    private String extractDeviceInfo(String userAgent) {
        if (userAgent == null) {
            return "unknown";
        }

        String deviceType = "Unknown";
        String os = "Unknown";
        String browser = "Unknown";

        if (userAgent.contains("Windows")) {
            os = "Windows";
        } else if (userAgent.contains("Mac")) {
            os = "macOS";
        } else if (userAgent.contains("Android")) {
            os = "Android";
            deviceType = "Mobile";
        } else if (userAgent.contains("iPhone") || userAgent.contains("iPad")) {
            os = "iOS";
            deviceType = "Mobile";
        } else if (userAgent.contains("Linux")) {
            os = "Linux";
        }

        if (userAgent.contains("Chrome")) {
            browser = "Chrome";
        } else if (userAgent.contains("Firefox")) {
            browser = "Firefox";
        } else if (userAgent.contains("Safari")) {
            browser = "Safari";
        } else if (userAgent.contains("Edge")) {
            browser = "Edge";
        }

        return os + "/" + browser + "/" + deviceType;
    }

    private void saveLoginHistory(User user, String ipAddress, String deviceInfo, 
                                   String userAgent, RiskAssessmentResult result) {
        UserLoginHistory history = new UserLoginHistory();
        history.setUserId(user.getId());
        history.setUsername(user.getUsername());
        history.setIpAddress(ipAddress);
        history.setDeviceInfo(deviceInfo);
        history.setUserAgent(userAgent);
        history.setLoginTime(LocalDateTime.now());
        history.setRiskLevel(result.getRiskLevel().name());
        history.setSuccess(true);

        loginHistoryRepository.save(history);

        List<UserLoginHistory> allHistory = loginHistoryRepository
                .findByUsernameOrderByLoginTimeDesc(user.getUsername());
        if (allHistory.size() > MAX_LOGIN_HISTORY) {
            for (int i = MAX_LOGIN_HISTORY; i < allHistory.size(); i++) {
                loginHistoryRepository.delete(allHistory.get(i));
            }
        }
    }

    public enum RiskLevel {
        LOW, MEDIUM, HIGH
    }

    public static class RiskAssessmentResult {
        private String username;
        private String ipAddress;
        private String userAgent;
        private String deviceInfo;
        private RiskLevel riskLevel = RiskLevel.LOW;
        private int riskScore = 0;
        private String message;
        private boolean requireAdditionalVerification = false;
        private List<String> warnings = new java.util.ArrayList<>();

        public static RiskAssessmentResult lowRisk(String message) {
            RiskAssessmentResult result = new RiskAssessmentResult();
            result.setRiskLevel(RiskLevel.LOW);
            result.setMessage(message);
            return result;
        }

        public String getUsername() { return username; }
        public void setUsername(String username) { this.username = username; }

        public String getIpAddress() { return ipAddress; }
        public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }

        public String getUserAgent() { return userAgent; }
        public void setUserAgent(String userAgent) { this.userAgent = userAgent; }

        public String getDeviceInfo() { return deviceInfo; }
        public void setDeviceInfo(String deviceInfo) { this.deviceInfo = deviceInfo; }

        public RiskLevel getRiskLevel() { return riskLevel; }
        public void setRiskLevel(RiskLevel riskLevel) { this.riskLevel = riskLevel; }

        public int getRiskScore() { return riskScore; }
        public void setRiskScore(int riskScore) { this.riskScore = riskScore; }

        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }

        public boolean isRequireAdditionalVerification() { return requireAdditionalVerification; }
        public void setRequireAdditionalVerification(boolean require) { this.requireAdditionalVerification = require; }

        public List<String> getWarnings() { return warnings; }
        public void addWarning(String warning) { this.warnings.add(warning); }
    }
}
