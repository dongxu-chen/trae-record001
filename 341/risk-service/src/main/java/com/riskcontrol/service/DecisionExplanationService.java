package com.riskcontrol.service;

import com.riskcontrol.common.enums.EventType;
import com.riskcontrol.common.enums.RiskLevel;
import com.riskcontrol.common.enums.RuleType;
import com.riskcontrol.common.model.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class DecisionExplanationService {

    private static final Logger logger = LoggerFactory.getLogger(DecisionExplanationService.class);

    private static final int TOP_FEATURES_COUNT = 5;

    private static final Map<String, String> FEATURE_DESCRIPTIONS = new HashMap<>();
    static {
        FEATURE_DESCRIPTIONS.put("eventType", "事件类型");
        FEATURE_DESCRIPTIONS.put("isProxy", "是否为代理IP");
        FEATURE_DESCRIPTIONS.put("isBlacklisted", "是否为黑名单IP");
        FEATURE_DESCRIPTIONS.put("isVpn", "是否为VPN");
        FEATURE_DESCRIPTIONS.put("isTor", "是否为TOR节点");
        FEATURE_DESCRIPTIONS.put("isDataCenter", "是否为数据中心IP");
        FEATURE_DESCRIPTIONS.put("loginAttemptCount", "登录尝试次数");
        FEATURE_DESCRIPTIONS.put("hoursSinceLastLogin", "距上次登录小时数");
        FEATURE_DESCRIPTIONS.put("isNewDevice", "是否为新设备");
        FEATURE_DESCRIPTIONS.put("deviceAssociationCount", "设备关联账号数");
        FEATURE_DESCRIPTIONS.put("velocityKmPerHour", "地理移动速度");
        FEATURE_DESCRIPTIONS.put("isAbnormalTime", "是否为异常登录时间");
        FEATURE_DESCRIPTIONS.put("countryRisk", "国家风险等级");
        FEATURE_DESCRIPTIONS.put("passwordStrength", "密码强度");
        FEATURE_DESCRIPTIONS.put("emailRisk", "邮箱风险");
        FEATURE_DESCRIPTIONS.put("accountAgeDays", "账号年龄");
        FEATURE_DESCRIPTIONS.put("fraudFlagCount", "历史欺诈标记数");
        FEATURE_DESCRIPTIONS.put("failedLoginCount", "历史失败登录数");
        FEATURE_DESCRIPTIONS.put("passwordChangeCount", "密码变更次数");
        FEATURE_DESCRIPTIONS.put("ipChangeCount", "IP变更次数");
    }

    public DecisionExplanation generateExplanation(RiskEvent event,
                                                   RiskAssessmentResult result,
                                                   UserBehaviorProfile profile,
                                                   FeatureVector features) {
        DecisionExplanation explanation = DecisionExplanation.builder()
                .riskLevel(result.getRiskLevel())
                .finalScore(result.getFinalScore())
                .explanationTimestamp(System.currentTimeMillis())
                .build();

        explanation.setRuleContributions(extractRuleContributions(result));
        explanation.setTopFeatureContributions(extractTopFeatureContributions(features, result));

        explanation.setRuleScoreContribution(result.getRuleScore());
        explanation.setMlScoreContribution(result.getMlScore());

        explanation.setSummary(generateSummary(result, event));
        explanation.setDetailedExplanation(generateDetailedExplanation(result, event, profile));

        explanation.setDecisionAction(determineAction(result));
        explanation.setActionReason(determineActionReason(result));
        explanation.setRecommendations(generateRecommendations(result, event));

        return explanation;
    }

    private List<RuleHit> extractRuleContributions(RiskAssessmentResult result) {
        List<RuleHit> hitRules = result.getHitRules();
        if (hitRules == null || hitRules.isEmpty()) {
            return Collections.emptyList();
        }

        return hitRules.stream()
                .sorted((r1, r2) -> Integer.compare(r2.getScore(), r1.getScore()))
                .peek(rule -> {
                    if (rule.getHitTimestamp() == 0) {
                        rule.setHitTimestamp(System.currentTimeMillis());
                    }
                })
                .collect(Collectors.toList());
    }

    private List<FeatureContribution> extractTopFeatureContributions(FeatureVector features,
                                                                     RiskAssessmentResult result) {
        if (features == null) {
            return Collections.emptyList();
        }

        double[] featureArray = features.toArray();
        String[] featureNames = features.getFeatureNames();

        if (featureArray == null || featureNames == null) {
            return Collections.emptyList();
        }

        List<FeatureContribution> contributions = new ArrayList<>();
        double mlScore = result.getMlScore() / 100.0;

        for (int i = 0; i < Math.min(featureArray.length, featureNames.length); i++) {
            double value = featureArray[i];
            if (Math.abs(value) < 0.001) continue;

            double contribution = Math.abs(value * mlScore);
            String direction = value > 0 ? "INCREASE_RISK" : "DECREASE_RISK";

            FeatureContribution fc = FeatureContribution.builder()
                    .featureName(featureNames[i])
                    .featureDescription(FEATURE_DESCRIPTIONS.getOrDefault(featureNames[i], featureNames[i]))
                    .featureValue(value)
                    .contribution(contribution)
                    .impactDirection(direction)
                    .category(determineCategory(featureNames[i]))
                    .build();

            contributions.add(fc);
        }

        contributions.sort((f1, f2) -> Double.compare(f2.getContribution(), f1.getContribution()));

        List<FeatureContribution> topFeatures = contributions.stream()
                .limit(TOP_FEATURES_COUNT)
                .collect(Collectors.toList());

        double totalContribution = topFeatures.stream()
                .mapToDouble(FeatureContribution::getContribution)
                .sum();

        for (FeatureContribution fc : topFeatures) {
            double percent = totalContribution > 0
                    ? (fc.getContribution() / totalContribution) * 100
                    : 0;
            fc.setContributionPercent(Math.round(percent * 100.0) / 100.0);
        }

        return topFeatures;
    }

    private String determineCategory(String featureName) {
        if (featureName.contains("device") || featureName.contains("canvas") ||
            featureName.contains("webgl") || featureName.contains("fonts")) {
            return FeatureContribution.Category.DEVICE.name();
        }
        if (featureName.contains("ip") || featureName.contains("proxy") ||
            featureName.contains("country") || featureName.contains("velocity")) {
            return FeatureContribution.Category.IP.name();
        }
        if (featureName.contains("login") || featureName.contains("password") ||
            featureName.contains("time") || featureName.contains("attempt")) {
            return FeatureContribution.Category.BEHAVIOR.name();
        }
        if (featureName.contains("fraud") || featureName.contains("age") ||
            featureName.contains("count")) {
            return FeatureContribution.Category.HISTORY.name();
        }
        return FeatureContribution.Category.CONTEXT.name();
    }

    private String generateSummary(RiskAssessmentResult result, RiskEvent event) {
        RiskLevel level = result.getRiskLevel();
        EventType type = event.getEventType();

        StringBuilder sb = new StringBuilder();
        sb.append(level.getDescription()).append("风险");

        if (type != null) {
            sb.append(" - ").append(getEventTypeDescription(type));
        }

        sb.append("，综合评分 ").append(result.getFinalScore()).append("分");

        if (result.getHitRules() != null && !result.getHitRules().isEmpty()) {
            sb.append("，触发").append(result.getHitRules().size()).append("条规则");
        }

        return sb.toString();
    }

    private String generateDetailedExplanation(RiskAssessmentResult result,
                                               RiskEvent event,
                                               UserBehaviorProfile profile) {
        StringBuilder sb = new StringBuilder();

        if (result.getRiskLevel() == RiskLevel.LOW) {
            sb.append("该操作风险较低，符合用户正常行为模式。");
        } else if (result.getRiskLevel() == RiskLevel.MEDIUM) {
            sb.append("该操作存在一定风险，建议关注后续行为。");
        } else if (result.getRiskLevel() == RiskLevel.HIGH) {
            sb.append("该操作风险较高，多项指标异常，建议加强验证。");
        } else if (result.getRiskLevel() == RiskLevel.CRITICAL) {
            sb.append("该操作风险极高，多项关键指标严重异常，存在明显欺诈特征。");
        }

        if (event.getIpInfo() != null) {
            IpInfo ipInfo = event.getIpInfo();
            if (ipInfo.isProxy() || ipInfo.isVpn() || ipInfo.isTor()) {
                sb.append(" 检测到使用");
                if (ipInfo.isTor()) sb.append("TOR网络");
                else if (ipInfo.isVpn()) sb.append("VPN");
                else sb.append("代理IP");
                sb.append("访问。");
            }
            if (ipInfo.isBlacklisted()) {
                sb.append(" IP地址在黑名单中。");
            }
        }

        if (event.getDeviceFingerprint() != null) {
            DeviceFingerprint df = event.getDeviceFingerprint();
            if (df.getAssociationCount() > 3) {
                sb.append(" 该设备已关联").append(df.getAssociationCount()).append("个账号，存在共享设备嫌疑。");
            }
        }

        if (event.getLoginAttemptCount() > 3) {
            sb.append(" 近期失败登录尝试").append(event.getLoginAttemptCount()).append("次。");
        }

        if (event.getVelocityKmPerHour() > 500) {
            sb.append(" 地理位置移动速度达到").append(Math.round(event.getVelocityKmPerHour()))
                    .append("km/h，存在不可能旅行特征。");
        }

        return sb.toString();
    }

    private String determineAction(RiskAssessmentResult result) {
        if (!result.isAllowed()) {
            if (result.isBlockAccount()) {
                return "BLOCK_ACCOUNT";
            }
            return "DENY";
        }
        if (result.isRequireMfa()) {
            return "REQUIRE_MFA";
        }
        if (result.isRequireCaptcha()) {
            return "REQUIRE_CAPTCHA";
        }
        return "ALLOW";
    }

    private String determineActionReason(RiskAssessmentResult result) {
        if (result.getFinalScore() >= 85) {
            return "风险评分过高，综合各项指标判定为高风险操作";
        }
        if (result.getFinalScore() >= 70) {
            return "存在多项异常特征，需要额外验证确认身份";
        }
        if (result.getFinalScore() >= 30) {
            return "存在少量异常特征，建议加强验证";
        }
        if (result.getFinalScore() > 0) {
            return "存在轻微异常，但在可接受范围内";
        }
        return "所有指标正常，无明显风险特征";
    }

    private List<String> generateRecommendations(RiskAssessmentResult result, RiskEvent event) {
        List<String> recommendations = new ArrayList<>();

        if (result.getFinalScore() >= 70) {
            recommendations.add("强制用户进行多因素认证");
            if (event.getEventType() == EventType.LOGIN) {
                recommendations.add("向用户发送异常登录提醒邮件");
            }
        }

        if (result.getFinalScore() >= 50) {
            recommendations.add("增加验证码验证");
            recommendations.add("记录本次操作详情以便后续审计");
        }

        if (event.getIpInfo() != null &&
                (event.getIpInfo().isProxy() || event.getIpInfo().isVpn())) {
            recommendations.add("提示用户关闭代理或VPN后重试");
        }

        if (event.getDeviceFingerprint() != null) {
            DeviceFingerprint df = event.getDeviceFingerprint();
            if (df.getAssociationCount() > 5) {
                recommendations.add("该设备关联账号过多，建议核查账号关联关系");
            }
        }

        if (result.getFinalScore() < 30) {
            recommendations.add("正常操作，无需额外处理");
        }

        return recommendations;
    }

    private String getEventTypeDescription(EventType type) {
        switch (type) {
            case LOGIN: return "登录操作";
            case REGISTER: return "注册操作";
            case PASSWORD_CHANGE: return "修改密码";
            case PASSWORD_RESET: return "重置密码";
            case EMAIL_CHANGE: return "修改邮箱";
            case PHONE_CHANGE: return "修改手机号";
            case PROFILE_UPDATE: return "更新资料";
            case SENSITIVE_OPERATION: return "敏感操作";
            default: return "未知操作";
        }
    }

    public String getRuleTypeDescription(RuleType ruleType) {
        if (ruleType == null) return "未知规则";
        switch (ruleType) {
            case IP_BLACKLIST: return "IP黑名单检测";
            case IP_PROXY: return "IP代理检测";
            case DEVICE_FINGERPRINT: return "设备指纹检测";
            case LOGIN_FREQUENCY: return "登录频率检测";
            case GEOLOCATION: return "地理位置检测";
            case PASSWORD_PATTERN: return "密码模式检测";
            case EMAIL_PATTERN: return "邮箱模式检测";
            case ABNORMAL_BEHAVIOR: return "异常行为检测";
            case CROSS_DEVICE: return "跨设备检测";
            case TIME_ANOMALY: return "时间异常检测";
            default: return "未知规则";
        }
    }
}
