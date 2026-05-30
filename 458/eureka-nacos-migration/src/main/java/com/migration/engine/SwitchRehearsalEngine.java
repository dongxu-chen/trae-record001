package com.migration.engine;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.model.ConsistencyCheckResult;
import com.migration.model.ServiceInstance;
import com.migration.model.SwitchRehearsal;
import com.migration.model.SwitchRehearsal.RehearsalResult;
import com.migration.model.SwitchRehearsal.RehearsalResult.RiskLevel;
import com.migration.model.SwitchRehearsal.RehearsalStatus;
import com.migration.model.SwitchRehearsal.RehearsalType;
import com.migration.model.SwitchRehearsal.SimulationStep;
import com.migration.model.SwitchRehearsal.SimulationStep.StepStatus;
import com.migration.model.SwitchRehearsal.SimulationStep.StepType;
import com.migration.verify.ConsistencyVerifier;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class SwitchRehearsalEngine {

    private final EurekaClient eurekaClient;
    private final NacosClient nacosClient;
    private final ConsistencyVerifier consistencyVerifier;
    private final RegistrySyncEngine registrySyncEngine;
    private final Map<String, SwitchRehearsal> rehearsals = new ConcurrentHashMap<>();

    public SwitchRehearsalEngine(EurekaClient eurekaClient,
                                 NacosClient nacosClient,
                                 ConsistencyVerifier consistencyVerifier,
                                 RegistrySyncEngine registrySyncEngine) {
        this.eurekaClient = eurekaClient;
        this.nacosClient = nacosClient;
        this.consistencyVerifier = consistencyVerifier;
        this.registrySyncEngine = registrySyncEngine;
    }

    public SwitchRehearsal createRehearsal(String name, RehearsalType type,
                                           List<String> targetServices, int targetPercentage) {
        String rehearsalId = UUID.randomUUID().toString();
        SwitchRehearsal rehearsal = SwitchRehearsal.builder()
                .rehearsalId(rehearsalId)
                .rehearsalName(name)
                .type(type)
                .status(RehearsalStatus.CREATED)
                .targetServices(targetServices != null ? targetServices : new ArrayList<>())
                .targetTrafficPercentage(targetPercentage)
                .createdAt(new Date())
                .build();

        rehearsals.put(rehearsalId, rehearsal);
        log.info("Created switch rehearsal: {} [{}]", name, rehearsalId);
        return rehearsal;
    }

    public SwitchRehearsal executeRehearsal(String rehearsalId) {
        SwitchRehearsal rehearsal = rehearsals.get(rehearsalId);
        if (rehearsal == null) {
            throw new IllegalArgumentException("Rehearsal not found: " + rehearsalId);
        }

        rehearsal.setStatus(RehearsalStatus.RUNNING);
        rehearsal.setStartTime(new Date());

        List<SimulationStep> steps = generateSimulationSteps(rehearsal);
        rehearsal.setSteps(steps);

        List<String> warnings = new ArrayList<>();
        List<String> errors = new ArrayList<>();
        List<String> recommendations = new ArrayList<>();
        int successfulSteps = 0;
        int warningSteps = 0;
        int failedSteps = 0;

        for (SimulationStep step : steps) {
            executeStep(step, rehearsal, warnings, errors, recommendations);

            switch (step.getStatus()) {
                case SUCCESS:
                    successfulSteps++;
                    break;
                case WARNING:
                    warningSteps++;
                    break;
                case FAILED:
                    failedSteps++;
                    break;
                default:
                    break;
            }
        }

        double riskScore = calculateRiskScore(successfulSteps, warningSteps, failedSteps, steps.size());
        RiskLevel riskLevel = determineRiskLevel(riskScore, warnings.size(), errors.size());

        RehearsalResult result = RehearsalResult.builder()
                .success(failedSteps == 0)
                .overallRiskScore(riskScore)
                .riskLevel(riskLevel)
                .totalSteps(steps.size())
                .successfulSteps(successfulSteps)
                .warningSteps(warningSteps)
                .failedSteps(failedSteps)
                .warnings(warnings)
                .errors(errors)
                .recommendations(recommendations)
                .summary(generateSummary(rehearsal, riskLevel, successfulSteps, steps.size()))
                .build();

        rehearsal.setResult(result);
        rehearsal.setStatus(failedSteps > 0 ? RehearsalStatus.FAILED : RehearsalStatus.COMPLETED);
        rehearsal.setCompletedTime(new Date());

        log.info("Rehearsal {} completed: status={}, riskScore={}, riskLevel={}",
                rehearsalId, rehearsal.getStatus(), riskScore, riskLevel);

        return rehearsal;
    }

    private List<SimulationStep> generateSimulationSteps(SwitchRehearsal rehearsal) {
        List<SimulationStep> steps = new ArrayList<>();
        int stepNum = 1;

        steps.add(createStep(stepNum++, "同步状态检查", StepType.SYNC_CHECK,
                "检查两个注册中心的同步状态"));
        steps.add(createStep(stepNum++, "服务健康检查", StepType.HEALTH_CHECK,
                "验证所有目标服务的健康状态"));
        steps.add(createStep(stepNum++, "元数据一致性校验", StepType.METADATA_VERIFY,
                "比对实例元数据一致性"));
        steps.add(createStep(stepNum++, "流量切换模拟", StepType.TRAFFIC_SHIFT,
                "模拟目标百分比的流量切换"));
        steps.add(createStep(stepNum++, "一致性校验", StepType.CONSISTENCY_CHECK,
                "执行完整的一致性检查"));
        steps.add(createStep(stepNum++, "性能基准测试", StepType.PERFORMANCE_TEST,
                "评估切换后的性能影响"));

        if (rehearsal.getType() == RehearsalType.ROLLBACK_SIMULATION) {
            steps.add(createStep(stepNum++, "回滚模拟", StepType.ROLLBACK_SIMULATION,
                    "模拟回滚到Eureka的过程"));
        }

        return steps;
    }

    private SimulationStep createStep(int number, String name, StepType type, String description) {
        return SimulationStep.builder()
                .stepNumber(number)
                .stepName(name)
                .type(type)
                .status(StepStatus.PENDING)
                .description(description)
                .metrics(new HashMap<>())
                .build();
    }

    private void executeStep(SimulationStep step, SwitchRehearsal rehearsal,
                             List<String> warnings, List<String> errors, List<String> recommendations) {
        step.setStatus(StepStatus.RUNNING);
        step.setStartTime(new Date());

        try {
            Map<String, Object> metrics = new HashMap<>();

            switch (step.getType()) {
                case SYNC_CHECK:
                    executeSyncCheck(step, metrics, warnings, recommendations);
                    break;
                case HEALTH_CHECK:
                    executeHealthCheck(step, rehearsal, metrics, warnings, errors);
                    break;
                case METADATA_VERIFY:
                    executeMetadataVerify(step, rehearsal, metrics, warnings);
                    break;
                case TRAFFIC_SHIFT:
                    executeTrafficShiftSimulation(step, rehearsal, metrics, warnings, recommendations);
                    break;
                case CONSISTENCY_CHECK:
                    executeConsistencyCheck(step, metrics, warnings, errors);
                    break;
                case PERFORMANCE_TEST:
                    executePerformanceTest(step, metrics, warnings);
                    break;
                case ROLLBACK_SIMULATION:
                    executeRollbackSimulation(step, rehearsal, metrics, warnings, recommendations);
                    break;
            }

            step.setMetrics(metrics);
            if (step.getStatus() == StepStatus.RUNNING) {
                step.setStatus(StepStatus.SUCCESS);
            }

        } catch (Exception e) {
            step.setStatus(StepStatus.FAILED);
            step.setErrorMessage(e.getMessage());
            errors.add(step.getStepName() + ": " + e.getMessage());
            log.error("Step {} failed: {}", step.getStepName(), e.getMessage());
        }

        step.setCompletedTime(new Date());
    }

    private void executeSyncCheck(SimulationStep step, Map<String, Object> metrics,
                                   List<String> warnings, List<String> recommendations) {
        List<String> eurekaServices = eurekaClient.getAllServiceIds();
        List<String> nacosServices = nacosClient.getAllServiceIds();

        metrics.put("eurekaServiceCount", eurekaServices.size());
        metrics.put("nacosServiceCount", nacosServices.size());

        Set<String> onlyInEureka = new HashSet<>(eurekaServices);
        onlyInEureka.removeAll(nacosServices);

        Set<String> onlyInNacos = new HashSet<>(nacosServices);
        onlyInNacos.removeAll(eurekaServices);

        metrics.put("onlyInEureka", onlyInEureka.size());
        metrics.put("onlyInNacos", onlyInNacos.size());

        if (!onlyInEureka.isEmpty() || !onlyInNacos.isEmpty()) {
            step.setStatus(StepStatus.WARNING);
            warnings.add("服务列表不一致: Eureka独有=" + onlyInEureka.size() + ", Nacos独有=" + onlyInNacos.size());
            recommendations.add("建议先执行注册中心同步，确保两边服务列表一致");
        }
    }

    private void executeHealthCheck(SimulationStep step, SwitchRehearsal rehearsal,
                                     Map<String, Object> metrics, List<String> warnings, List<String> errors) {
        List<String> services = rehearsal.getTargetServices();
        if (services.isEmpty()) {
            services = eurekaClient.getAllServiceIds();
        }

        int healthyEureka = 0;
        int healthyNacos = 0;
        List<String> unhealthyInEureka = new ArrayList<>();
        List<String> unhealthyInNacos = new ArrayList<>();

        for (String serviceId : services) {
            List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
            List<ServiceInstance> nacosInstances = nacosClient.getInstances(serviceId);

            boolean eurekaHealthy = !eurekaInstances.isEmpty() &&
                    eurekaInstances.stream().allMatch(i -> "UP".equals(i.getStatus()));
            boolean nacosHealthy = nacosInstances.isEmpty() ||
                    nacosInstances.stream().allMatch(i -> "UP".equals(i.getStatus()));

            if (eurekaHealthy) healthyEureka++;
            else unhealthyInEureka.add(serviceId);

            if (nacosHealthy) healthyNacos++;
            else unhealthyInNacos.add(serviceId);
        }

        metrics.put("totalServices", services.size());
        metrics.put("healthyInEureka", healthyEureka);
        metrics.put("healthyInNacos", healthyNacos);
        metrics.put("unhealthyInEureka", unhealthyInEureka);
        metrics.put("unhealthyInNacos", unhealthyInNacos);

        if (!unhealthyInEureka.isEmpty()) {
            step.setStatus(StepStatus.WARNING);
            warnings.add("Eureka中有 " + unhealthyInEureka.size() + " 个服务不健康");
        }
    }

    private void executeMetadataVerify(SimulationStep step, SwitchRehearsal rehearsal,
                                        Map<String, Object> metrics, List<String> warnings) {
        List<String> services = rehearsal.getTargetServices();
        if (services.isEmpty()) {
            services = eurekaClient.getAllServiceIds();
        }

        int totalInstances = 0;
        int instancesWithDiffs = 0;
        List<String> servicesWithMetadataIssues = new ArrayList<>();

        for (String serviceId : services) {
            List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
            List<ServiceInstance> nacosInstances = nacosClient.getInstances(serviceId);

            totalInstances += eurekaInstances.size();

            ConsistencyCheckResult result = consistencyVerifier.quickVerify();
            if (result.getDifferences() != null && !result.getDifferences().isEmpty()) {
                instancesWithDiffs++;
                servicesWithMetadataIssues.add(serviceId);
            }
        }

        metrics.put("totalInstances", totalInstances);
        metrics.put("instancesWithMetadataDiffs", instancesWithDiffs);
        metrics.put("servicesWithMetadataIssues", servicesWithMetadataIssues);

        if (instancesWithDiffs > 0) {
            step.setStatus(StepStatus.WARNING);
            warnings.add("发现 " + instancesWithDiffs + " 个服务存在元数据差异");
        }
    }

    private void executeTrafficShiftSimulation(SimulationStep step, SwitchRehearsal rehearsal,
                                                Map<String, Object> metrics, List<String> warnings,
                                                List<String> recommendations) {
        int targetPercentage = rehearsal.getTargetTrafficPercentage();
        List<String> services = rehearsal.getTargetServices();

        metrics.put("targetTrafficPercentage", targetPercentage);
        metrics.put("affectedServices", services.size());
        metrics.put("estimatedTrafficShift", targetPercentage + "%");

        double riskFactor = targetPercentage / 100.0;
        metrics.put("trafficShiftRisk", String.format("%.2f", riskFactor * 0.3));

        if (targetPercentage > 50) {
            step.setStatus(StepStatus.WARNING);
            warnings.add("流量切换比例超过50%，建议采用更保守的灰度策略");
            recommendations.add("建议分阶段增加流量比例，每阶段增加不超过20%");
        }

        if (targetPercentage == 100) {
            recommendations.add("全量切换前建议先执行回滚演练");
        }
    }

    private void executeConsistencyCheck(SimulationStep step, Map<String, Object> metrics,
                                          List<String> warnings, List<String> errors) {
        ConsistencyCheckResult result = consistencyVerifier.quickVerify();

        metrics.put("consistent", result.isConsistent());
        metrics.put("totalServices", result.getTotalServices());
        metrics.put("matchedServices", result.getMatchedServices());
        metrics.put("mismatchedServices", result.getMismatchedServices());
        metrics.put("onlyInEureka", result.getOnlyInEureka());
        metrics.put("onlyInNacos", result.getOnlyInNacos());
        metrics.put("alertCount", result.getAlerts() != null ? result.getAlerts().size() : 0);

        if (!result.isConsistent()) {
            step.setStatus(StepStatus.WARNING);
            warnings.add("一致性检查发现 " + result.getMismatchedServices() + " 个服务不一致");
        }
    }

    private void executePerformanceTest(SimulationStep step, Map<String, Object> metrics,
                                         List<String> warnings) {
        long eurekaStart = System.currentTimeMillis();
        eurekaClient.getAllServiceIds();
        long eurekaTime = System.currentTimeMillis() - eurekaStart;

        long nacosStart = System.currentTimeMillis();
        nacosClient.getAllServiceIds();
        long nacosTime = System.currentTimeMillis() - nacosStart;

        metrics.put("eurekaDiscoveryTimeMs", eurekaTime);
        metrics.put("nacosDiscoveryTimeMs", nacosTime);
        metrics.put("performanceDiffPct", String.format("%.1f%%",
                (nacosTime - eurekaTime) * 100.0 / Math.max(eurekaTime, 1)));

        if (nacosTime > eurekaTime * 1.5) {
            step.setStatus(StepStatus.WARNING);
            warnings.add("Nacos查询性能比Eureka慢50%以上");
        }
    }

    private void executeRollbackSimulation(SimulationStep step, SwitchRehearsal rehearsal,
                                            Map<String, Object> metrics, List<String> warnings,
                                            List<String> recommendations) {
        List<String> services = rehearsal.getTargetServices();
        metrics.put("servicesToRollback", services.size());
        metrics.put("estimatedRollbackTimeMs", services.size() * 500L);
        metrics.put("rollbackComplexity", services.size() > 10 ? "HIGH" : services.size() > 5 ? "MEDIUM" : "LOW");

        recommendations.add("回滚前建议保存当前Nacos服务状态快照");
        recommendations.add("回滚操作应在低峰期执行");
    }

    private double calculateRiskScore(int success, int warning, int failed, int total) {
        if (total == 0) return 0;
        double score = (success * 0 + warning * 0.3 + failed * 1.0) / total;
        return Math.min(1.0, score);
    }

    private RiskLevel determineRiskLevel(double riskScore, int warningCount, int errorCount) {
        if (errorCount > 0 || riskScore >= 0.7) {
            return RiskLevel.CRITICAL;
        } else if (riskScore >= 0.4 || warningCount > 3) {
            return RiskLevel.HIGH;
        } else if (riskScore >= 0.2 || warningCount > 0) {
            return RiskLevel.MEDIUM;
        }
        return RiskLevel.LOW;
    }

    private String generateSummary(SwitchRehearsal rehearsal, RiskLevel riskLevel,
                                    int successCount, int totalCount) {
        return String.format("演练'%s'完成: %d/%d步骤成功, 风险等级=%s",
                rehearsal.getRehearsalName(), successCount, totalCount, riskLevel);
    }

    public SwitchRehearsal getRehearsal(String rehearsalId) {
        return rehearsals.get(rehearsalId);
    }

    public List<SwitchRehearsal> getAllRehearsals() {
        return new ArrayList<>(rehearsals.values());
    }

    public void deleteRehearsal(String rehearsalId) {
        rehearsals.remove(rehearsalId);
    }
}
