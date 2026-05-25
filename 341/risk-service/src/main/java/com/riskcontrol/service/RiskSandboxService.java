package com.riskcontrol.service;

import com.riskcontrol.common.enums.EventType;
import com.riskcontrol.common.enums.RiskLevel;
import com.riskcontrol.common.model.*;
import com.riskcontrol.ml.engine.FeatureEngineeringService;
import com.riskcontrol.ml.engine.MLScoringService;
import com.riskcontrol.rules.engine.RuleEngineService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class RiskSandboxService {

    private static final Logger logger = LoggerFactory.getLogger(RiskSandboxService.class);

    private final RuleEngineService ruleEngineService;
    private final MLScoringService mlScoringService;
    private final FeatureEngineeringService featureEngineeringService;
    private final DecisionExplanationService explanationService;
    private final EventPreprocessingService preprocessingService;

    @Autowired
    public RiskSandboxService(RuleEngineService ruleEngineService,
                              MLScoringService mlScoringService,
                              FeatureEngineeringService featureEngineeringService,
                              DecisionExplanationService explanationService,
                              EventPreprocessingService preprocessingService) {
        this.ruleEngineService = ruleEngineService;
        this.mlScoringService = mlScoringService;
        this.featureEngineeringService = featureEngineeringService;
        this.explanationService = explanationService;
        this.preprocessingService = preprocessingService;
    }

    public SandboxResult simulateAssessment(RiskEvent event, SandboxConfig config) {
        long startTime = System.currentTimeMillis();

        if (event.getEventId() == null || event.getEventId().isEmpty()) {
            event.setEventId("sandbox-" + UUID.randomUUID().toString());
        }
        if (event.getEventTimestamp() == 0) {
            event.setEventTimestamp(System.currentTimeMillis());
        }

        logger.info("Starting sandbox assessment for event: {}, type: {}", event.getEventId(), event.getEventType());

        preprocessingService.preprocessEvent(event);
        enrichSandboxEvent(event, config);

        RiskAssessmentResult result = ruleEngineService.evaluateRules(event);

        FeatureVector features = null;
        UserBehaviorProfile profile = buildSandboxProfile(config);

        if (config.isEnableML() && mlScoringService.isModelReady()) {
            result = mlScoringService.scoreWithML(event, profile, result);
            features = featureEngineeringService.buildFeatureVector(event, profile);
        } else {
            result.setFinalScore(result.getRuleScore());
        }

        RiskLevel finalLevel = RiskLevel.fromScore(result.getFinalScore());
        result.setRiskLevel(finalLevel);
        result.setIsAllowed(result.getFinalScore() < 90);

        if (result.getFinalScore() >= 70) {
            result.setRequireMfa(true);
        }
        if (result.getFinalScore() >= 85) {
            result.setBlockAccount(true);
            result.setIsAllowed(false);
        }

        DecisionExplanation explanation = explanationService.generateExplanation(event, result, profile, features);
        result.setExplanation(explanation);

        long processingTime = System.currentTimeMillis() - startTime;
        result.setProcessingTimeMs(processingTime);
        result.setAssessmentTimestamp(System.currentTimeMillis());

        SandboxResult sandboxResult = SandboxResult.builder()
                .eventId(event.getEventId())
                .originalEvent(event)
                .assessmentResult(result)
                .features(features)
                .profile(profile)
                .config(config)
                .processingTimeMs(processingTime)
                .build();

        if (config.isShowComparison()) {
            sandboxResult.setComparison(generateComparison(event, result, config));
        }

        if (config.isShowWhatIf()) {
            sandboxResult.setWhatIfScenarios(generateWhatIfScenarios(event, profile, config));
        }

        logger.info("Sandbox assessment completed for event {}: score={}, level={}",
                event.getEventId(), result.getFinalScore(), result.getRiskLevel());

        return sandboxResult;
    }

    private void enrichSandboxEvent(RiskEvent event, SandboxConfig config) {
        if (config.getIpInfo() != null) {
            event.setIpInfo(config.getIpInfo());
        }

        if (config.getDeviceFingerprint() != null) {
            event.setDeviceFingerprint(config.getDeviceFingerprint());
        }

        if (config.getLoginAttemptCount() > 0) {
            event.setLoginAttemptCount(config.getLoginAttemptCount());
        }

        if (config.getVelocityKmPerHour() > 0) {
            event.setVelocityKmPerHour(config.getVelocityKmPerHour());
        }

        if (config.getLastLoginTimestamp() > 0) {
            event.setLastLoginTimestamp(config.getLastLoginTimestamp());
        }

        if (config.getLastLoginIp() != null) {
            event.setLastLoginIp(config.getLastLoginIp());
        }

        if (config.getLastLoginDeviceId() != null) {
            event.setLastLoginDeviceId(config.getLastLoginDeviceId());
        }
    }

    private UserBehaviorProfile buildSandboxProfile(SandboxConfig config) {
        UserBehaviorProfile.UserBehaviorProfileBuilder builder = UserBehaviorProfile.builder()
                .userId(config.getUserId() != null ? config.getUserId() : "sandbox-user")
                .accountCreationTimestamp(System.currentTimeMillis() - (config.getAccountAgeDays() * 86400000L))
                .fraudFlagCount(config.getFraudFlagCount())
                .failedLoginCount(config.getFailedLoginCount())
                .passwordChangeCount(config.getPasswordChangeCount())
                .usualLoginStartHour(config.getUsualLoginStartHour())
                .usualLoginEndHour(config.getUsualLoginEndHour());

        Set<String> commonIps = new HashSet<>();
        if (config.getCommonIp() != null) {
            commonIps.add(config.getCommonIp());
        }
        builder.commonIpAddresses(commonIps);

        Set<String> commonDevices = new HashSet<>();
        if (config.getCommonDeviceId() != null) {
            commonDevices.add(config.getCommonDeviceId());
        }
        builder.commonDeviceIds(commonDevices);

        Set<String> commonCountries = new HashSet<>();
        if (config.getCommonCountry() != null) {
            commonCountries.add(config.getCommonCountry());
        }
        builder.commonCountries(commonCountries);

        return builder.build();
    }

    private SandboxComparison generateComparison(RiskEvent event, RiskAssessmentResult result, SandboxConfig config) {
        SandboxComparison comparison = new SandboxComparison();

        comparison.setRuleScore(result.getRuleScore());
        comparison.setMlScore(result.getMlScore());
        comparison.setFinalScore(result.getFinalScore());

        if (config.getBaselineScore() > 0) {
            comparison.setBaselineScore(config.getBaselineScore());
            comparison.setScoreDifference(result.getFinalScore() - config.getBaselineScore());
        }

        comparison.setRuleCount(result.getHitRules() != null ? result.getHitRules().size() : 0);
        comparison.setBlocked(!result.isAllowed());
        comparison.setRequireMfa(result.isRequireMfa());
        comparison.setRequireCaptcha(result.isRequireCaptcha());

        List<String> contributingFactors = new ArrayList<>();
        if (result.getHitRules() != null) {
            for (RuleHit hit : result.getHitRules()) {
                if (hit.getScore() >= 20) {
                    contributingFactors.add(hit.getDescription());
                }
            }
        }
        comparison.setTopContributingFactors(contributingFactors);

        return comparison;
    }

    private List<WhatIfScenario> generateWhatIfScenarios(RiskEvent originalEvent,
                                                          UserBehaviorProfile profile,
                                                          SandboxConfig config) {
        List<WhatIfScenario> scenarios = new ArrayList<>();

        if (config.getWhatIfScenarios() == null || config.getWhatIfScenarios().isEmpty()) {
            scenarios.add(createWhatIfScenario(originalEvent, profile, "无代理 IP", e -> {
                if (e.getIpInfo() != null) {
                    e.getIpInfo().setProxy(false);
                    e.getIpInfo().setVpn(false);
                }
            }));

            scenarios.add(createWhatIfScenario(originalEvent, profile, "使用 VPN", e -> {
                if (e.getIpInfo() != null) {
                    e.getIpInfo().setProxy(true);
                    e.getIpInfo().setVpn(true);
                }
            }));

            scenarios.add(createWhatIfScenario(originalEvent, profile, "使用 TOR", e -> {
                if (e.getIpInfo() != null) {
                    e.getIpInfo().setProxy(true);
                    e.getIpInfo().setTor(true);
                }
            }));

            scenarios.add(createWhatIfScenario(originalEvent, profile, "5次失败尝试", e -> {
                e.setLoginAttemptCount(5);
            }));

            scenarios.add(createWhatIfScenario(originalEvent, profile, "高速移动(1200km/h)", e -> {
                e.setVelocityKmPerHour(1200);
            }));

            scenarios.add(createWhatIfScenario(originalEvent, profile, "黑名单IP", e -> {
                if (e.getIpInfo() != null) {
                    e.getIpInfo().setBlacklisted(true);
                }
            }));
        } else {
            for (Map<String, Object> scenarioConfig : config.getWhatIfScenarios()) {
                String name = (String) scenarioConfig.get("name");
                @SuppressWarnings("unchecked")
                Map<String, Object> modifications = (Map<String, Object>) scenarioConfig.get("modifications");
                scenarios.add(createWhatIfScenario(originalEvent, profile, name, e -> applyModifications(e, modifications)));
            }
        }

        return scenarios;
    }

    private WhatIfScenario createWhatIfScenario(RiskEvent originalEvent, UserBehaviorProfile profile,
                                                 String scenarioName, java.util.function.Consumer<RiskEvent> modifier) {
        try {
            RiskEvent scenarioEvent = cloneEvent(originalEvent);
            modifier.accept(scenarioEvent);

            RiskAssessmentResult result = ruleEngineService.evaluateRules(scenarioEvent);

            if (mlScoringService.isModelReady()) {
                result = mlScoringService.scoreWithML(scenarioEvent, profile, result);
            } else {
                result.setFinalScore(result.getRuleScore());
            }

            RiskLevel level = RiskLevel.fromScore(result.getFinalScore());
            result.setRiskLevel(level);
            result.setIsAllowed(result.getFinalScore() < 90);

            WhatIfScenario scenario = new WhatIfScenario();
            scenario.setScenarioName(scenarioName);
            scenario.setFinalScore(result.getFinalScore());
            scenario.setRiskLevel(level);
            scenario.setAllowed(result.getFinalScore() < 90);
            scenario.setRuleScore(result.getRuleScore());
            scenario.setMlScore(result.getMlScore());

            int originalScore = originalEvent.getRuleScore();
            scenario.setScoreChange(result.getFinalScore() - originalScore);

            List<String> triggeredRules = new ArrayList<>();
            if (result.getHitRules() != null) {
                for (RuleHit hit : result.getHitRules()) {
                    triggeredRules.add(hit.getDescription());
                }
            }
            scenario.setTriggeredRules(triggeredRules);

            return scenario;

        } catch (Exception e) {
            logger.error("Failed to generate what-if scenario: {}", scenarioName, e);
            WhatIfScenario scenario = new WhatIfScenario();
            scenario.setScenarioName(scenarioName);
            scenario.setError(e.getMessage());
            return scenario;
        }
    }

    private RiskEvent cloneEvent(RiskEvent original) {
        return RiskEvent.builder()
                .eventId(original.getEventId())
                .userId(original.getUserId())
                .account(original.getAccount())
                .eventType(original.getEventType())
                .eventTimestamp(original.getEventTimestamp())
                .ipAddress(original.getIpAddress())
                .userAgent(original.getUserAgent())
                .ipInfo(original.getIpInfo() != null ?
                        IpInfo.builder()
                                .ipAddress(original.getIpInfo().getIpAddress())
                                .country(original.getIpInfo().getCountry())
                                .region(original.getIpInfo().getRegion())
                                .city(original.getIpInfo().getCity())
                                .latitude(original.getIpInfo().getLatitude())
                                .longitude(original.getIpInfo().getLongitude())
                                .isp(original.getIpInfo().getIsp())
                                .isProxy(original.getIpInfo().isProxy())
                                .isVpn(original.getIpInfo().isVpn())
                                .isTor(original.getIpInfo().isTor())
                                .isDataCenter(original.getIpInfo().isDataCenter())
                                .isBlacklisted(original.getIpInfo().isBlacklisted())
                                .riskScore(original.getIpInfo().getRiskScore())
                                .build() : null)
                .deviceFingerprint(original.getDeviceFingerprint())
                .loginAttemptCount(original.getLoginAttemptCount())
                .velocityKmPerHour(original.getVelocityKmPerHour())
                .lastLoginTimestamp(original.getLastLoginTimestamp())
                .lastLoginIp(original.getLastLoginIp())
                .lastLoginDeviceId(original.getLastLoginDeviceId())
                .email(original.getEmail())
                .phone(original.getPhone())
                .newPasswordHash(original.getNewPasswordHash())
                .sessionId(original.getSessionId())
                .referer(original.getReferer())
                .build();
    }

    private void applyModifications(RiskEvent event, Map<String, Object> modifications) {
        if (modifications == null) return;

        for (Map.Entry<String, Object> entry : modifications.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();

            switch (key) {
                case "loginAttemptCount":
                    event.setLoginAttemptCount(((Number) value).intValue());
                    break;
                case "velocityKmPerHour":
                    event.setVelocityKmPerHour(((Number) value).doubleValue());
                    break;
                case "isProxy":
                    if (event.getIpInfo() != null) event.getIpInfo().setProxy((Boolean) value);
                    break;
                case "isVpn":
                    if (event.getIpInfo() != null) event.getIpInfo().setVpn((Boolean) value);
                    break;
                case "isTor":
                    if (event.getIpInfo() != null) event.getIpInfo().setTor((Boolean) value);
                    break;
                case "isBlacklisted":
                    if (event.getIpInfo() != null) event.getIpInfo().setBlacklisted((Boolean) value);
                    break;
                case "isDataCenter":
                    if (event.getIpInfo() != null) event.getIpInfo().setDataCenter((Boolean) value);
                    break;
            }
        }
    }

    public SandboxResult batchSimulate(List<RiskEvent> events, SandboxConfig config) {
        if (events == null || events.isEmpty()) {
            throw new IllegalArgumentException("No test events provided");
        }

        List<RiskAssessmentResult> results = new ArrayList<>();
        for (RiskEvent event : events) {
            SandboxResult result = simulateAssessment(event, config);
            results.add(result.getAssessmentResult());
        }

        SandboxResult summary = new SandboxResult();
        summary.setBatchResults(results);

        int totalScore = 0;
        int blocked = 0;
        int mfa = 0;
        Map<RiskLevel, Integer> levelCounts = new EnumMap<>(RiskLevel.class);

        for (RiskAssessmentResult result : results) {
            totalScore += result.getFinalScore();
            if (!result.isAllowed()) blocked++;
            if (result.isRequireMfa()) mfa++;
            levelCounts.merge(result.getRiskLevel(), 1, Integer::sum);
        }

        Map<String, Object> stats = new HashMap<>();
        stats.put("totalTests", results.size());
        stats.put("averageScore", Math.round((totalScore * 1.0 / results.size()) * 100) / 100.0);
        stats.put("blockedCount", blocked);
        stats.put("blockedRate", Math.round((blocked * 100.0 / results.size()) * 100) / 100.0);
        stats.put("mfaCount", mfa);
        stats.put("mfaRate", Math.round((mfa * 100.0 / results.size()) * 100) / 100.0);
        stats.put("levelDistribution", levelCounts);

        summary.setBatchStats(stats);

        return summary;
    }

    public static class SandboxConfig {
        private String userId;
        private IpInfo ipInfo;
        private DeviceFingerprint deviceFingerprint;
        private int loginAttemptCount;
        private double velocityKmPerHour;
        private long lastLoginTimestamp;
        private String lastLoginIp;
        private String lastLoginDeviceId;
        private boolean enableML = true;
        private boolean showComparison = true;
        private boolean showWhatIf = true;
        private int baselineScore;
        private int accountAgeDays = 30;
        private int fraudFlagCount = 0;
        private int failedLoginCount = 0;
        private int passwordChangeCount = 0;
        private int usualLoginStartHour = 8;
        private int usualLoginEndHour = 22;
        private String commonIp;
        private String commonDeviceId;
        private String commonCountry = "CN";
        private List<Map<String, Object>> whatIfScenarios;

        public String getUserId() { return userId; }
        public void setUserId(String userId) { this.userId = userId; }
        public IpInfo getIpInfo() { return ipInfo; }
        public void setIpInfo(IpInfo ipInfo) { this.ipInfo = ipInfo; }
        public DeviceFingerprint getDeviceFingerprint() { return deviceFingerprint; }
        public void setDeviceFingerprint(DeviceFingerprint deviceFingerprint) { this.deviceFingerprint = deviceFingerprint; }
        public int getLoginAttemptCount() { return loginAttemptCount; }
        public void setLoginAttemptCount(int loginAttemptCount) { this.loginAttemptCount = loginAttemptCount; }
        public double getVelocityKmPerHour() { return velocityKmPerHour; }
        public void setVelocityKmPerHour(double velocityKmPerHour) { this.velocityKmPerHour = velocityKmPerHour; }
        public long getLastLoginTimestamp() { return lastLoginTimestamp; }
        public void setLastLoginTimestamp(long lastLoginTimestamp) { this.lastLoginTimestamp = lastLoginTimestamp; }
        public String getLastLoginIp() { return lastLoginIp; }
        public void setLastLoginIp(String lastLoginIp) { this.lastLoginIp = lastLoginIp; }
        public String getLastLoginDeviceId() { return lastLoginDeviceId; }
        public void setLastLoginDeviceId(String lastLoginDeviceId) { this.lastLoginDeviceId = lastLoginDeviceId; }
        public boolean isEnableML() { return enableML; }
        public void setEnableML(boolean enableML) { this.enableML = enableML; }
        public boolean isShowComparison() { return showComparison; }
        public void setShowComparison(boolean showComparison) { this.showComparison = showComparison; }
        public boolean isShowWhatIf() { return showWhatIf; }
        public void setShowWhatIf(boolean showWhatIf) { this.showWhatIf = showWhatIf; }
        public int getBaselineScore() { return baselineScore; }
        public void setBaselineScore(int baselineScore) { this.baselineScore = baselineScore; }
        public int getAccountAgeDays() { return accountAgeDays; }
        public void setAccountAgeDays(int accountAgeDays) { this.accountAgeDays = accountAgeDays; }
        public int getFraudFlagCount() { return fraudFlagCount; }
        public void setFraudFlagCount(int fraudFlagCount) { this.fraudFlagCount = fraudFlagCount; }
        public int getFailedLoginCount() { return failedLoginCount; }
        public void setFailedLoginCount(int failedLoginCount) { this.failedLoginCount = failedLoginCount; }
        public int getPasswordChangeCount() { return passwordChangeCount; }
        public void setPasswordChangeCount(int passwordChangeCount) { this.passwordChangeCount = passwordChangeCount; }
        public int getUsualLoginStartHour() { return usualLoginStartHour; }
        public void setUsualLoginStartHour(int usualLoginStartHour) { this.usualLoginStartHour = usualLoginStartHour; }
        public int getUsualLoginEndHour() { return usualLoginEndHour; }
        public void setUsualLoginEndHour(int usualLoginEndHour) { this.usualLoginEndHour = usualLoginEndHour; }
        public String getCommonIp() { return commonIp; }
        public void setCommonIp(String commonIp) { this.commonIp = commonIp; }
        public String getCommonDeviceId() { return commonDeviceId; }
        public void setCommonDeviceId(String commonDeviceId) { this.commonDeviceId = commonDeviceId; }
        public String getCommonCountry() { return commonCountry; }
        public void setCommonCountry(String commonCountry) { this.commonCountry = commonCountry; }
        public List<Map<String, Object>> getWhatIfScenarios() { return whatIfScenarios; }
        public void setWhatIfScenarios(List<Map<String, Object>> whatIfScenarios) { this.whatIfScenarios = whatIfScenarios; }
    }

    @lombok.Data
    @lombok.Builder
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class SandboxResult {
        private String eventId;
        private RiskEvent originalEvent;
        private RiskAssessmentResult assessmentResult;
        private FeatureVector features;
        private UserBehaviorProfile profile;
        private SandboxConfig config;
        private long processingTimeMs;
        private SandboxComparison comparison;
        private List<WhatIfScenario> whatIfScenarios;
        private List<RiskAssessmentResult> batchResults;
        private Map<String, Object> batchStats;
    }

    @lombok.Data
    public static class SandboxComparison {
        private int ruleScore;
        private int mlScore;
        private int finalScore;
        private int baselineScore;
        private int scoreDifference;
        private int ruleCount;
        private boolean blocked;
        private boolean requireMfa;
        private boolean requireCaptcha;
        private List<String> topContributingFactors;
    }

    @lombok.Data
    public static class WhatIfScenario {
        private String scenarioName;
        private int finalScore;
        private RiskLevel riskLevel;
        private boolean allowed;
        private int ruleScore;
        private int mlScore;
        private int scoreChange;
        private List<String> triggeredRules;
        private String error;
    }
}
