package com.sessionguard.engine;

import com.sessionguard.config.SessionGuardProperties;
import com.sessionguard.model.*;
import lombok.RequiredArgsConstructor;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class RiskScoringEngine {

    private final SessionGuardProperties properties;

    public RiskAssessment assess(SessionProfile current, SessionProfile previous, String businessScenario) {
        SessionGuardProperties.RiskWeights weights = properties.getRiskWeights();
        SessionGuardProperties.BusinessScenarioConfig scenarioConfig = properties.getScenarioConfig(businessScenario);

        List<RiskFactor> factors = new ArrayList<>();
        int totalScore = 0;

        if (previous != null) {
            totalScore += analyzeIpChange(current, previous, factors, weights.getIpChange());
            totalScore += analyzeGeoChange(current, previous, factors, weights.getGeoCountryChange(), weights.getGeoRegionChange());
            totalScore += analyzeSubnetChange(current, previous, factors, weights.getSubnetChange());
            totalScore += analyzeFingerprintChange(current, previous, factors, weights.getFingerprintChange());
            totalScore += analyzeCookieAnomaly(current, previous, factors, weights.getCookieAnomaly());
            totalScore += analyzeUserAgentChange(current, previous, factors, weights.getUserAgentChange());
            totalScore += analyzeRapidChange(current, previous, factors, weights.getRapidChange());
            totalScore += analyzeTimeAnomaly(current, previous, factors, weights.getTimeAnomaly());
        }

        totalScore += analyzeNetworkContext(current, factors, weights.getTor(), weights.getProxyVpn(), weights.getDataCenter());

        totalScore = Math.min(totalScore, 100);

        RiskAssessment.RiskLevel riskLevel = determineRiskLevel(totalScore, scenarioConfig.getThresholds());

        return RiskAssessment.builder()
                .sessionId(current.getSessionId())
                .userId(current.getUserId())
                .totalScore(totalScore)
                .riskLevel(riskLevel)
                .riskFactors(factors)
                .assessedAt(LocalDateTime.now())
                .requiresAction(riskLevel == RiskAssessment.RiskLevel.HIGH
                        || riskLevel == RiskAssessment.RiskLevel.CRITICAL)
                .recommendedAction(determineAction(riskLevel, scenarioConfig))
                .build();
    }

    public RiskAssessment assess(SessionProfile current, SessionProfile previous) {
        return assess(current, previous, properties.getDefaultBusinessScenario());
    }

    private int analyzeIpChange(SessionProfile current, SessionProfile previous, List<RiskFactor> factors, int weight) {
        if (previous.getIpContext() == null || current.getIpContext() == null) {
            return 0;
        }

        String prevIp = previous.getIpContext().getIpAddress();
        String currIp = current.getIpContext().getIpAddress();

        if (!StringUtils.equals(prevIp, currIp)) {
            factors.add(RiskFactor.builder()
                    .category("IP")
                    .name("IP_ADDRESS_CHANGED")
                    .description("IP address changed from " + prevIp + " to " + currIp)
                    .weight(weight)
                    .score(weight)
                    .detail("Previous: " + prevIp + ", Current: " + currIp)
                    .build());
            return weight;
        }
        return 0;
    }

    private int analyzeGeoChange(SessionProfile current, SessionProfile previous, List<RiskFactor> factors, int countryWeight, int regionWeight) {
        if (previous.getIpContext() == null || current.getIpContext() == null) {
            return 0;
        }

        String prevCountry = previous.getIpContext().getGeoCountry();
        String currCountry = current.getIpContext().getGeoCountry();
        String prevRegion = previous.getIpContext().getGeoRegion();
        String currRegion = current.getIpContext().getGeoRegion();

        int score = 0;
        if (!StringUtils.equals(prevCountry, currCountry) && !"UNKNOWN".equals(prevCountry)) {
            score += countryWeight;
            factors.add(RiskFactor.builder()
                    .category("GEO")
                    .name("COUNTRY_CHANGED")
                    .description("Country changed from " + prevCountry + " to " + currCountry)
                    .weight(countryWeight)
                    .score(countryWeight)
                    .detail("Previous: " + prevCountry + ", Current: " + currCountry)
                    .build());
        } else if (!StringUtils.equals(prevRegion, currRegion) && !"UNKNOWN".equals(prevRegion)) {
            int regionScore = regionWeight;
            score += regionScore;
            factors.add(RiskFactor.builder()
                    .category("GEO")
                    .name("REGION_CHANGED")
                    .description("Region changed from " + prevRegion + " to " + currRegion)
                    .weight(regionWeight)
                    .score(regionScore)
                    .detail("Previous: " + prevRegion + ", Current: " + currRegion)
                    .build());
        }

        return score;
    }

    private int analyzeSubnetChange(SessionProfile current, SessionProfile previous, List<RiskFactor> factors, int weight) {
        if (previous.getIpContext() == null || current.getIpContext() == null) {
            return 0;
        }

        String prevSubnet = previous.getIpContext().getSubnetPrefix();
        String currSubnet = current.getIpContext().getSubnetPrefix();

        if (!StringUtils.equals(prevSubnet, currSubnet)) {
            factors.add(RiskFactor.builder()
                    .category("IP")
                    .name("SUBNET_CHANGED")
                    .description("Subnet changed from " + prevSubnet + " to " + currSubnet)
                    .weight(weight)
                    .score(weight)
                    .detail("Previous: " + prevSubnet + ", Current: " + currSubnet)
                    .build());
            return weight;
        }
        return 0;
    }

    private int analyzeFingerprintChange(SessionProfile current, SessionProfile previous, List<RiskFactor> factors, int weight) {
        if (previous.getDeviceFingerprint() == null || current.getDeviceFingerprint() == null) {
            return 0;
        }

        String prevHash = previous.getDeviceFingerprint().getFingerprintHash();
        String currHash = current.getDeviceFingerprint().getFingerprintHash();

        if (!StringUtils.equals(prevHash, currHash)) {
            double similarity = computeFingerprintSimilarity(
                    previous.getDeviceFingerprint(), current.getDeviceFingerprint());

            int score;
            if (similarity < 0.3) {
                score = weight;
            } else if (similarity < 0.7) {
                score = weight * 2 / 3;
            } else {
                score = weight / 3;
            }

            factors.add(RiskFactor.builder()
                    .category("FINGERPRINT")
                    .name("DEVICE_FINGERPRINT_CHANGED")
                    .description("Device fingerprint changed (similarity: "
                            + String.format("%.2f", similarity) + ")")
                    .weight(weight)
                    .score(score)
                    .detail("Previous hash: " + prevHash + ", Current hash: " + currHash
                            + ", Similarity: " + String.format("%.4f", similarity))
                    .build());
            return score;
        }
        return 0;
    }

    private int analyzeCookieAnomaly(SessionProfile current, SessionProfile previous, List<RiskFactor> factors, int weight) {
        if (previous.getCookieId() == null || current.getCookieId() == null) {
            return 0;
        }

        if (!StringUtils.equals(previous.getCookieId(), current.getCookieId())) {
            factors.add(RiskFactor.builder()
                    .category("COOKIE")
                    .name("COOKIE_ID_CHANGED")
                    .description("Session cookie ID was unexpectedly changed")
                    .weight(weight)
                    .score(weight)
                    .detail("Previous: " + previous.getCookieId() + ", Current: " + current.getCookieId())
                    .build());
            return weight;
        }
        return 0;
    }

    private int analyzeUserAgentChange(SessionProfile current, SessionProfile previous, List<RiskFactor> factors, int weight) {
        if (previous.getDeviceFingerprint() == null || current.getDeviceFingerprint() == null) {
            return 0;
        }

        String prevUa = previous.getDeviceFingerprint().getUserAgent();
        String currUa = current.getDeviceFingerprint().getUserAgent();

        if (!StringUtils.equals(prevUa, currUa)) {
            factors.add(RiskFactor.builder()
                    .category("FINGERPRINT")
                    .name("USER_AGENT_CHANGED")
                    .description("User-Agent string changed")
                    .weight(weight)
                    .score(weight)
                    .detail("Previous: " + prevUa)
                    .build());
            return weight;
        }
        return 0;
    }

    private int analyzeRapidChange(SessionProfile current, SessionProfile previous, List<RiskFactor> factors, int weight) {
        if (previous.getLastAccessedAt() == null || current.getLastAccessedAt() == null) {
            return 0;
        }

        Duration gap = Duration.between(previous.getLastAccessedAt(), current.getLastAccessedAt());
        boolean ipChanged = !StringUtils.equals(
                previous.getIpContext() != null ? previous.getIpContext().getIpAddress() : null,
                current.getIpContext() != null ? current.getIpContext().getIpAddress() : null);

        if (ipChanged && gap.toMinutes() < 5) {
            factors.add(RiskFactor.builder()
                    .category("BEHAVIOR")
                    .name("RAPID_IP_CHANGE")
                    .description("IP changed within 5 minutes (gap: " + gap.toSeconds() + "s)")
                    .weight(weight)
                    .score(weight)
                    .detail("Time gap: " + gap.toSeconds() + " seconds")
                    .build());
            return weight;
        }
        return 0;
    }

    private int analyzeTimeAnomaly(SessionProfile current, SessionProfile previous, List<RiskFactor> factors, int weight) {
        if (previous.getLastAccessedAt() == null) {
            return 0;
        }

        Duration inactivity = Duration.between(previous.getLastAccessedAt(), LocalDateTime.now());
        if (inactivity.toHours() > 8 && current.getAccessCount() > 1) {
            factors.add(RiskFactor.builder()
                    .category("BEHAVIOR")
                    .name("UNUSUAL_ACTIVITY_TIME")
                    .description("Session activity after " + inactivity.toHours() + " hours of inactivity")
                    .weight(weight)
                    .score(weight)
                    .detail("Inactive for: " + inactivity.toHours() + " hours")
                    .build());
            return weight;
        }
        return 0;
    }

    private int analyzeNetworkContext(SessionProfile current, List<RiskFactor> factors, int torWeight, int proxyVpnWeight, int dataCenterWeight) {
        int score = 0;

        if (current.getIpContext() != null) {
            if (current.getIpContext().isTor()) {
                score += torWeight;
                factors.add(RiskFactor.builder()
                        .category("NETWORK")
                        .name("TOR_DETECTED")
                        .description("Connection via Tor network detected")
                        .weight(torWeight)
                        .score(torWeight)
                        .detail("IP: " + current.getIpContext().getIpAddress())
                        .build());
            }

            if (current.getIpContext().isProxy()) {
                score += proxyVpnWeight;
                factors.add(RiskFactor.builder()
                        .category("NETWORK")
                        .name("PROXY_DETECTED")
                        .description("Connection via proxy detected")
                        .weight(proxyVpnWeight)
                        .score(proxyVpnWeight)
                        .detail("IP: " + current.getIpContext().getIpAddress())
                        .build());
            }

            if (current.getIpContext().isVpn()) {
                score += proxyVpnWeight;
                factors.add(RiskFactor.builder()
                        .category("NETWORK")
                        .name("VPN_DETECTED")
                        .description("Connection via VPN detected")
                        .weight(proxyVpnWeight)
                        .score(proxyVpnWeight)
                        .detail("IP: " + current.getIpContext().getIpAddress())
                        .build());
            }

            if (current.getIpContext().isDataCenter()) {
                score += dataCenterWeight;
                factors.add(RiskFactor.builder()
                        .category("NETWORK")
                        .name("DATACENTER_IP")
                        .description("IP belongs to a data center range")
                        .weight(dataCenterWeight)
                        .score(dataCenterWeight)
                        .detail("ISP: " + current.getIpContext().getIsp())
                        .build());
            }
        }

        return score;
    }

    public int assessConcurrentSessionRisk(int concurrentCount, String businessScenario) {
        SessionGuardProperties.RiskWeights weights = properties.getRiskWeights();
        if (concurrentCount <= 1) return 0;
        int score = weights.getConcurrentSession() * (concurrentCount - 1);
        return Math.min(score, weights.getConcurrentSession() * 3);
    }

    public int assessConcurrentSessionRisk(int concurrentCount) {
        return assessConcurrentSessionRisk(concurrentCount, properties.getDefaultBusinessScenario());
    }

    double computeFingerprintSimilarity(DeviceFingerprint fp1, DeviceFingerprint fp2) {
        int matches = 0;
        int total = 0;

        total++;
        if (StringUtils.equals(fp1.getBrowser(), fp2.getBrowser())) matches++;

        total++;
        if (StringUtils.equals(fp1.getOs(), fp2.getOs())) matches++;

        total++;
        if (StringUtils.equals(fp1.getPlatform(), fp2.getPlatform())) matches++;

        total++;
        if (StringUtils.equals(fp1.getTimezone(), fp2.getTimezone())) matches++;

        total++;
        if (StringUtils.equals(fp1.getLanguage(), fp2.getLanguage())) matches++;

        total++;
        if (StringUtils.equals(fp1.getScreenResolution(), fp2.getScreenResolution())) matches++;

        if (fp1.getCanvasHash() != null && fp2.getCanvasHash() != null
                && !fp1.getCanvasHash().isEmpty() && !fp2.getCanvasHash().isEmpty()) {
            total++;
            if (mapSimilarity(fp1.getCanvasHash(), fp2.getCanvasHash()) > 0.8) matches++;
        }

        if (fp1.getWebglHash() != null && fp2.getWebglHash() != null
                && !fp1.getWebglHash().isEmpty() && !fp2.getWebglHash().isEmpty()) {
            total++;
            if (mapSimilarity(fp1.getWebglHash(), fp2.getWebglHash()) > 0.8) matches++;
        }

        return total > 0 ? (double) matches / total : 0.0;
    }

    private double mapSimilarity(Map<String, String> map1, Map<String, String> map2) {
        if (map1.isEmpty() && map2.isEmpty()) return 1.0;
        int matches = 0;
        int total = Math.max(map1.size(), map2.size());
        for (Map.Entry<String, String> entry : map1.entrySet()) {
            if (StringUtils.equals(entry.getValue(), map2.get(entry.getKey()))) {
                matches++;
            }
        }
        return total > 0 ? (double) matches / total : 0.0;
    }

    private RiskAssessment.RiskLevel determineRiskLevel(int score, SessionGuardProperties.RiskThresholds thresholds) {
        if (score < thresholds.getLow()) {
            return RiskAssessment.RiskLevel.LOW;
        } else if (score < thresholds.getMedium()) {
            return RiskAssessment.RiskLevel.MEDIUM;
        } else if (score < thresholds.getHigh()) {
            return RiskAssessment.RiskLevel.HIGH;
        } else {
            return RiskAssessment.RiskLevel.CRITICAL;
        }
    }

    private String determineAction(RiskAssessment.RiskLevel riskLevel, SessionGuardProperties.BusinessScenarioConfig scenarioConfig) {
        return switch (riskLevel) {
            case LOW -> "MONITOR";
            case MEDIUM -> "FLAG_AND_MONITOR";
            case HIGH -> scenarioConfig.isRequireReauthOnHigh() ? "REQUIRE_RE_AUTHENTICATION" : "FLAG_AND_MONITOR";
            case CRITICAL -> scenarioConfig.isAutoInvalidateOnCritical() ? "INVALIDATE_SESSION_IMMEDIATELY" : "REQUIRE_RE_AUTHENTICATION";
        };
    }
}
