package com.mfa.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "mfa")
public class MfaProperties {

    private Sms sms = new Sms();
    private Email email = new Email();
    private Totp totp = new Totp();
    private WebAuthn webauthn = new WebAuthn();
    private Jwt jwt = new Jwt();
    private Risk risk = new Risk();
    private Adaptive adaptive = new Adaptive();

    @Data
    public static class Sms {
        private int expireMinutes = 5;
        private int codeLength = 6;
    }

    @Data
    public static class Email {
        private int expireMinutes = 10;
        private int codeLength = 6;
    }

    @Data
    public static class Totp {
        private int timeStep = 30;
        private int digits = 6;
        private int windowSize = 1;
    }

    @Data
    public static class WebAuthn {
        private String relyingPartyId = "localhost";
        private String relyingPartyName = "MFA Authentication Service";
        private String origin = "http://localhost:8080";
    }

    @Data
    public static class Jwt {
        private String secret;
        private long expirationMs = 86400000;
    }

    @Data
    public static class Risk {
        private int thresholdMedium = 30;
        private int thresholdHigh = 70;
        private int maxRiskScore = 100;
    }

    @Data
    public static class Adaptive {
        private boolean trustedDeviceBypassEnabled = true;
        private int trustedDeviceDays = 30;
        private boolean stepUpEnabled = true;
        private int lowRiskRequiredFactors = 1;
        private int mediumRiskRequiredFactors = 2;
        private int highRiskRequiredFactors = 3;
        private int criticalRiskRequiredFactors = 4;
    }
}
