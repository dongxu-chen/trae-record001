package com.riskcontrol.ml.engine;

import com.riskcontrol.common.enums.EventType;
import com.riskcontrol.common.model.FeatureVector;
import com.riskcontrol.common.model.RiskEvent;
import com.riskcontrol.common.model.UserBehaviorProfile;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Pattern;

@Service
public class FeatureEngineeringService {

    private static final Logger logger = LoggerFactory.getLogger(FeatureEngineeringService.class);

    private static final Set<String> HIGH_RISK_EMAIL_DOMAINS = new HashSet<>(Arrays.asList(
            "throwaway.com", "tempmail.com", "dispostable.com",
            "guerrillamail.com", "fakeinbox.com", "mailinator.com"
    ));

    private static final Set<String> HIGH_RISK_COUNTRIES = new HashSet<>(Arrays.asList(
            "KP", "IR", "SY", "CF", "SO", "SS", "LY", "YE"
    ));

    public FeatureVector buildFeatureVector(RiskEvent event, UserBehaviorProfile profile) {
        FeatureVector.FeatureVectorBuilder builder = FeatureVector.builder();

        builder.eventType(event.getEventType() != null ? event.getEventType().ordinal() : 0);

        int isProxyIp = 0;
        int isBlacklistedIp = 0;
        if (event.getIpInfo() != null) {
            isProxyIp = (event.getIpInfo().isProxy() || event.getIpInfo().isVpn() ||
                    event.getIpInfo().isTor() || event.getIpInfo().isDataCenter()) ? 1 : 0;
            isBlacklistedIp = event.getIpInfo().isBlacklisted() ? 1 : 0;
        }
        builder.isProxyIp(isProxyIp);
        builder.isBlacklistedIp(isBlacklistedIp);

        builder.loginAttemptCount(Math.min(event.getLoginAttemptCount(), 20));

        double timeSinceLastLogin = event.getLastLoginTimestamp() > 0
                ? (event.getEventTimestamp() - event.getLastLoginTimestamp()) / 3600000.0
                : 168.0;
        builder.timeSinceLastLogin(Math.min(timeSinceLastLogin, 168.0));

        int differentDevice = (event.getLastLoginDeviceId() != null &&
                event.getDeviceFingerprint() != null &&
                !event.getLastLoginDeviceId().equals(event.getDeviceFingerprint().getDeviceId())) ? 1 : 0;
        builder.differentDevice(differentDevice);

        int differentIp = (event.getLastLoginIp() != null &&
                !event.getLastLoginIp().equals(event.getIpAddress())) ? 1 : 0;
        builder.differentIp(differentIp);

        builder.velocity(Math.min(event.getVelocityKmPerHour(), 2000.0));

        int unusualHour = isUnusualHour(event.getEventTimestamp(), profile) ? 1 : 0;
        builder.unusualHour(unusualHour);

        int unusualLocation = isUnusualLocation(event, profile) ? 1 : 0;
        builder.unusualLocation(unusualLocation);

        String newPassword = event.getNewPasswordHash();
        if (newPassword != null) {
            builder.passwordLength(Math.min(newPassword.length(), 30));
            builder.passwordComplexity(calculatePasswordComplexity(newPassword));
        } else {
            builder.passwordLength(0);
            builder.passwordComplexity(0);
        }

        builder.emailDomainRisk(calculateEmailDomainRisk(event.getEmail()));

        builder.phoneRisk(calculatePhoneRisk(event.getPhone()));

        int deviceAgeDays = 0;
        if (event.getDeviceFingerprint() != null && event.getDeviceFingerprint().getFirstSeenTimestamp() > 0) {
            deviceAgeDays = (int) ((event.getEventTimestamp() -
                    event.getDeviceFingerprint().getFirstSeenTimestamp()) / 86400000L);
        }
        builder.deviceAgeDays(Math.min(deviceAgeDays, 365));

        int accountAgeDays = profile != null && profile.getAccountCreationTimestamp() > 0
                ? (int) ((event.getEventTimestamp() - profile.getAccountCreationTimestamp()) / 86400000L)
                : 365;
        builder.accountAgeDays(Math.min(accountAgeDays, 365));

        builder.historicalFraudCount(profile != null ? Math.min(profile.getFraudFlagCount(), 10) : 0);

        builder.ruleScore(event.getRuleScore());

        builder.crossDeviceCount(profile != null ? Math.min(profile.getCommonDeviceIds().size(), 10) : 0);

        builder.ipChangeFrequency(profile != null ? Math.min(profile.getCommonIpAddresses().size(), 10) : 0);

        return builder.build();
    }

    private boolean isUnusualHour(long timestamp, UserBehaviorProfile profile) {
        if (profile != null) {
            int hour = (int) ((timestamp / 3600000) % 24);
            int startHour = profile.getUsualLoginStartHour();
            int endHour = profile.getUsualLoginEndHour();
            if (startHour != endHour) {
                if (startHour < endHour) {
                    return hour < startHour || hour >= endHour;
                } else {
                    return hour >= endHour && hour < startHour;
                }
            }
        }
        int hour = (int) ((timestamp / 3600000) % 24);
        return hour >= 2 && hour < 6;
    }

    private boolean isUnusualLocation(RiskEvent event, UserBehaviorProfile profile) {
        if (profile == null || profile.getCommonCountries() == null) {
            if (event.getIpInfo() != null && event.getIpInfo().getCountry() != null) {
                return HIGH_RISK_COUNTRIES.contains(event.getIpInfo().getCountry());
            }
            return false;
        }
        if (event.getIpInfo() != null && event.getIpInfo().getCountry() != null) {
            String country = event.getIpInfo().getCountry();
            return !profile.getCommonCountries().contains(country) ||
                    HIGH_RISK_COUNTRIES.contains(country);
        }
        return false;
    }

    private int calculatePasswordComplexity(String password) {
        if (password == null || password.isEmpty()) return 0;
        int score = 0;
        if (password.length() >= 8) score++;
        if (password.length() >= 12) score++;
        if (Pattern.compile("[a-z]").matcher(password).find()) score++;
        if (Pattern.compile("[A-Z]").matcher(password).find()) score++;
        if (Pattern.compile("[0-9]").matcher(password).find()) score++;
        if (Pattern.compile("[!@#$%^&*(),.?\":{}|<>]").matcher(password).find()) score++;
        return score;
    }

    private int calculateEmailDomainRisk(String email) {
        if (email == null || !email.contains("@")) return 0;
        String domain = email.split("@")[1].toLowerCase();
        if (HIGH_RISK_EMAIL_DOMAINS.contains(domain)) return 3;
        if (domain.contains("temp") || domain.contains("throw") || domain.contains("fake")) return 2;
        if (domain.endsWith(".ru") || domain.endsWith(".cn") || domain.endsWith(".nk")) return 1;
        return 0;
    }

    private int calculatePhoneRisk(String phone) {
        if (phone == null || phone.isEmpty()) return 0;
        String digits = phone.replaceAll("\\D", "");
        if (digits.length() < 7) return 3;
        if (digits.startsWith("+86") && digits.length() != 13) return 2;
        if (digits.startsWith("+1") && digits.length() != 12) return 2;
        if (digits.matches("(\\d)\\1{6,}")) return 3;
        if (digits.matches("12345678|87654321")) return 2;
        return 0;
    }
}
