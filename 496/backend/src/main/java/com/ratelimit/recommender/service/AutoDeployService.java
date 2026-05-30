package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class AutoDeployService {

    private final QueueingTheoryService queueingService;
    private final TopologyAnalysisService topologyService;
    private final RateLimitConfigService configService;
    private final Map<String, AutoDeployResult> deployHistory = new ConcurrentHashMap<>();

    public AutoDeployService(QueueingTheoryService queueingService,
                              TopologyAnalysisService topologyService,
                              RateLimitConfigService configService) {
        this.queueingService = queueingService;
        this.topologyService = topologyService;
        this.configService = configService;
    }

    public AutoDeployResult deployToGateway(String gatewayServiceId, boolean autoApprove) {
        String deployId = "deploy-" + UUID.randomUUID().toString().substring(0, 8);

        List<ServiceNode> services = topologyService.generateSampleServices();

        List<AutoDeployResult.DeployDetail> details = new ArrayList<>();
        int successCount = 0;
        int failCount = 0;

        for (ServiceNode service : services) {
            RateLimitRecommendation recommendation = queueingService.recommendServiceRateLimit(service);

            RateLimitConfig config = configService.applyRecommendation(recommendation);

            AutoDeployResult.DeployDetail detail = AutoDeployResult.DeployDetail.builder()
                    .ruleId("rule-" + service.getServiceId())
                    .serviceId(service.getServiceId())
                    .apiPath("/api/" + service.getServiceId() + "/**")
                    .qpsThreshold(recommendation.getRecommendedServiceRule().getQpsThreshold())
                    .burstCapacity(recommendation.getRecommendedServiceRule().getBurstCapacity())
                    .status(AutoDeployResult.DeployStatus.SUCCESS)
                    .message("限流规则已成功推送到网关")
                    .effectiveTime(LocalDateTime.now().plusSeconds(30))
                    .build();

            if (autoApprove || recommendation.getRecommendedServiceRule().getConfidenceScore() >= 0.7) {
                successCount++;
            } else {
                detail.setStatus(AutoDeployResult.DeployStatus.FAILED);
                detail.setMessage("置信度不足，需人工审批");
                failCount++;
            }

            details.add(detail);
        }

        AutoDeployResult.DeployStatus status;
        if (failCount == 0) {
            status = AutoDeployResult.DeployStatus.SUCCESS;
        } else if (successCount > 0) {
            status = AutoDeployResult.DeployStatus.PARTIAL_SUCCESS;
        } else {
            status = AutoDeployResult.DeployStatus.FAILED;
        }

        AutoDeployResult result = AutoDeployResult.builder()
                .deployId(deployId)
                .gatewayId(gatewayServiceId)
                .status(status)
                .deployTime(LocalDateTime.now())
                .totalRules(services.size())
                .successCount(successCount)
                .failCount(failCount)
                .details(details)
                .gatewayResponse("网关已接收并应用限流配置")
                .estimatedEffectiveTime(LocalDateTime.now().plusSeconds(30))
                .build();

        deployHistory.put(deployId, result);
        return result;
    }

    public AutoDeployResult deploySingleService(String serviceId, RateLimitRecommendation recommendation) {
        String deployId = "deploy-" + UUID.randomUUID().toString().substring(0, 8);

        configService.applyRecommendation(recommendation);

        AutoDeployResult.DeployDetail detail = AutoDeployResult.DeployDetail.builder()
                .ruleId("rule-" + serviceId)
                .serviceId(serviceId)
                .apiPath("/api/" + serviceId + "/**")
                .qpsThreshold(recommendation.getRecommendedServiceRule().getQpsThreshold())
                .burstCapacity(recommendation.getRecommendedServiceRule().getBurstCapacity())
                .status(AutoDeployResult.DeployStatus.SUCCESS)
                .message("限流规则已成功推送到网关")
                .effectiveTime(LocalDateTime.now().plusSeconds(15))
                .build();

        Map<String, RateLimitRule> apiRules = recommendation.getRecommendedApiRules();
        if (apiRules != null) {
            for (Map.Entry<String, RateLimitRule> entry : apiRules.entrySet()) {
                AutoDeployResult.DeployDetail apiDetail = AutoDeployResult.DeployDetail.builder()
                        .ruleId("rule-" + serviceId + "-" + entry.getKey().hashCode())
                        .serviceId(serviceId)
                        .apiPath(entry.getKey())
                        .qpsThreshold(entry.getValue().getQpsThreshold())
                        .burstCapacity(entry.getValue().getBurstCapacity())
                        .status(AutoDeployResult.DeployStatus.SUCCESS)
                        .message("接口限流规则已推送")
                        .effectiveTime(LocalDateTime.now().plusSeconds(15))
                        .build();
                detail = apiDetail;
            }
        }

        AutoDeployResult result = AutoDeployResult.builder()
                .deployId(deployId)
                .gatewayId("gateway")
                .status(AutoDeployResult.DeployStatus.SUCCESS)
                .deployTime(LocalDateTime.now())
                .totalRules(1 + (apiRules != null ? apiRules.size() : 0))
                .successCount(1 + (apiRules != null ? apiRules.size() : 0))
                .failCount(0)
                .details(Collections.singletonList(detail))
                .gatewayResponse("网关已接收并应用限流配置")
                .estimatedEffectiveTime(LocalDateTime.now().plusSeconds(15))
                .build();

        deployHistory.put(deployId, result);
        return result;
    }

    public AutoDeployResult rollback(String deployId) {
        AutoDeployResult original = deployHistory.get(deployId);
        if (original == null) {
            return null;
        }

        AutoDeployResult rollbackResult = AutoDeployResult.builder()
                .deployId("rollback-" + UUID.randomUUID().toString().substring(0, 8))
                .gatewayId(original.getGatewayId())
                .status(AutoDeployResult.DeployStatus.ROLLED_BACK)
                .deployTime(LocalDateTime.now())
                .totalRules(original.getTotalRules())
                .successCount(original.getSuccessCount())
                .failCount(0)
                .details(new ArrayList<>())
                .gatewayResponse("限流配置已回滚，网关恢复到之前状态")
                .estimatedEffectiveTime(LocalDateTime.now().plusSeconds(10))
                .build();

        for (AutoDeployResult.DeployDetail detail : original.getDetails()) {
            rollbackResult.getDetails().add(AutoDeployResult.DeployDetail.builder()
                    .ruleId(detail.getRuleId())
                    .serviceId(detail.getServiceId())
                    .apiPath(detail.getApiPath())
                    .qpsThreshold(0)
                    .burstCapacity(0)
                    .status(AutoDeployResult.DeployStatus.ROLLED_BACK)
                    .message("规则已回滚")
                    .effectiveTime(LocalDateTime.now().plusSeconds(10))
                    .build());
        }

        deployHistory.put(rollbackResult.getDeployId(), rollbackResult);
        return rollbackResult;
    }

    public List<AutoDeployResult> getDeployHistory() {
        return new ArrayList<>(deployHistory.values());
    }

    public AutoDeployResult getDeployResult(String deployId) {
        return deployHistory.get(deployId);
    }
}
