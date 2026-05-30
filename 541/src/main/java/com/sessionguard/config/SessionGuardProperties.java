package com.sessionguard.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Data
@Component
@ConfigurationProperties(prefix = "session-guard")
public class SessionGuardProperties {

    private String defaultBusinessScenario = "STANDARD";

    private RiskWeights riskWeights = new RiskWeights();

    private Map<String, BusinessScenarioConfig> businessScenarios = new HashMap<>();

    private UserGuidanceConfig userGuidance = new UserGuidanceConfig();

    private SessionConfig session = new SessionConfig();

    private ActiveInvalidationConfig activeInvalidation = new ActiveInvalidationConfig();

    public BusinessScenarioConfig getScenarioConfig(String scenario) {
        return businessScenarios.getOrDefault(scenario, businessScenarios.get(defaultBusinessScenario));
    }

    public boolean isActiveInvalidationEnabled() {
        return activeInvalidation.isEnabled();
    }

    @Data
    public static class RiskWeights {
        private int ipChange = 25;
        private int geoCountryChange = 30;
        private int geoRegionChange = 15;
        private int subnetChange = 15;
        private int fingerprintChange = 30;
        private int cookieAnomaly = 20;
        private int proxyVpn = 20;
        private int tor = 35;
        private int dataCenter = 15;
        private int rapidChange = 25;
        private int concurrentSession = 20;
        private int userAgentChange = 15;
        private int timeAnomaly = 10;
        private int mlAnomaly = 30;
    }

    @Data
    public static class BusinessScenarioConfig {
        private String description;
        private RiskThresholds thresholds = new RiskThresholds();
        private boolean autoInvalidateOnCritical = true;
        private boolean requireReauthOnHigh = true;
        private String friendlyMessage;
    }

    @Data
    public static class RiskThresholds {
        private int low = 30;
        private int medium = 60;
        private int high = 80;
        private int critical = 95;
    }

    @Data
    public static class UserGuidanceConfig {
        private String reauthUrl = "/login?prompt=reauth";
        private String supportContact = "请联系客服获取帮助";
        private int maxReauthAttempts = 3;
        private int reauthCooldownMinutes = 5;
    }

    @Data
    public static class SessionConfig {
        private int ttlMinutes = 120;
        private int maxConcurrentSessions = 5;
    }

    @Data
    public static class ActiveInvalidationConfig {
        private boolean enabled = true;
        private boolean autoInvalidateOnCritical = true;
        private boolean notifyUserOnInvalidation = true;
    }
}
