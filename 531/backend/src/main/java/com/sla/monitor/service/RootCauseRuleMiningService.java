package com.sla.monitor.service;

import com.sla.monitor.model.RootCauseAnalysis;
import com.sla.monitor.model.RootCauseRule;
import com.sla.monitor.model.SlaMetrics;
import com.sla.monitor.repository.RootCauseAnalysisRepository;
import com.sla.monitor.repository.RootCauseRuleRepository;
import com.sla.monitor.repository.SlaMetricsRepository;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class RootCauseRuleMiningService {

    private static final Logger logger = LoggerFactory.getLogger(RootCauseRuleMiningService.class);

    private final RootCauseRuleRepository ruleRepository;
    private final RootCauseAnalysisRepository analysisRepository;
    private final SlaMetricsRepository metricsRepository;

    private static final int MIN_SUPPORT_THRESHOLD = 5;
    private static final int MIN_CONFIDENCE_THRESHOLD = 60;

    public RootCauseRuleMiningService(RootCauseRuleRepository ruleRepository,
                                       RootCauseAnalysisRepository analysisRepository,
                                       SlaMetricsRepository metricsRepository) {
        this.ruleRepository = ruleRepository;
        this.analysisRepository = analysisRepository;
        this.metricsRepository = metricsRepository;
    }

    @Scheduled(cron = "0 0 2 * * ?")
    public void scheduledRuleMining() {
        logger.info("Starting scheduled root cause rule mining...");
        try {
            int newRules = mineRulesFromHistoricalData();
            logger.info("Scheduled rule mining completed. Found {} new rules.", newRules);
        } catch (Exception e) {
            logger.error("Scheduled rule mining failed", e);
        }
    }

    public int mineRulesFromHistoricalData() {
        LocalDateTime startTime = LocalDateTime.now().minusDays(30);
        List<RootCauseAnalysis> historicalAnalyses = analysisRepository
                .findAll().stream()
                .filter(a -> a.getTimestamp().isAfter(startTime))
                .collect(Collectors.toList());

        if (historicalAnalyses.size() < MIN_SUPPORT_THRESHOLD) {
            logger.info("Not enough historical data for rule mining. Found {} records, need at least {}.",
                    historicalAnalyses.size(), MIN_SUPPORT_THRESHOLD);
            return 0;
        }

        Map<RootCauseAnalysis.RootCauseCategory, List<RootCauseAnalysis>> groupedAnalyses =
                historicalAnalyses.stream()
                        .collect(Collectors.groupingBy(RootCauseAnalysis::getPrimaryCause));

        int newRulesCount = 0;

        for (Map.Entry<RootCauseAnalysis.RootCauseCategory, List<RootCauseAnalysis>> entry :
                groupedAnalyses.entrySet()) {
            RootCauseAnalysis.RootCauseCategory causeType = entry.getKey();
            List<RootCauseAnalysis> analyses = entry.getValue();

            if (analyses.size() >= MIN_SUPPORT_THRESHOLD) {
                Optional<RootCauseRule> newRule = mineRule(causeType, analyses);
                if (newRule.isPresent() && !ruleRepository.existsByRuleCode(newRule.get().getRuleCode())) {
                    ruleRepository.save(newRule.get());
                    newRulesCount++;
                    logger.info("Mined new rule: {} for cause type: {}",
                            newRule.get().getRuleCode(), causeType);
                }
            }
        }

        updateRuleStatistics();
        return newRulesCount;
    }

    private Optional<RootCauseRule> mineRule(RootCauseAnalysis.RootCauseCategory causeType,
                                              List<RootCauseAnalysis> analyses) {
        Set<String> serviceNames = analyses.stream()
                .map(RootCauseAnalysis::getServiceName)
                .collect(Collectors.toSet());

        List<SlaMetrics> violationMetrics = new ArrayList<>();
        for (String serviceName : serviceNames) {
            for (RootCauseAnalysis analysis : analyses) {
                if (analysis.getServiceName().equals(serviceName)) {
                    LocalDateTime eventTime = analysis.getTimestamp();
                    List<SlaMetrics> metrics = metricsRepository.findByServiceNameAndTimeRange(
                            serviceName,
                            eventTime.minusHours(1),
                            eventTime.plusHours(1)
                    );
                    violationMetrics.addAll(metrics);
                }
            }
        }

        if (violationMetrics.isEmpty()) {
            return Optional.empty();
        }

        DescriptiveStatistics availabilityStats = new DescriptiveStatistics();
        DescriptiveStatistics latencyStats = new DescriptiveStatistics();
        DescriptiveStatistics errorRateStats = new DescriptiveStatistics();

        for (SlaMetrics metrics : violationMetrics) {
            if (metrics.getAvailability() != null) {
                availabilityStats.addValue(metrics.getAvailability());
            }
            if (metrics.getAvgLatencyMs() != null) {
                latencyStats.addValue(metrics.getAvgLatencyMs());
            }
            if (metrics.getErrorRate() != null) {
                errorRateStats.addValue(metrics.getErrorRate());
            }
        }

        if (availabilityStats.getN() < MIN_SUPPORT_THRESHOLD) {
            return Optional.empty();
        }

        double confidence = calculateConfidence(analyses.size(), causeType);
        if (confidence < MIN_CONFIDENCE_THRESHOLD) {
            return Optional.empty();
        }

        RootCauseRule rule = new RootCauseRule();
        rule.setRuleCode(generateRuleCode(causeType));
        rule.setRuleName(generateRuleName(causeType));
        rule.setDescription("Auto-mined rule for " + causeType + " from " + analyses.size() + " historical events");
        rule.setRootCauseType(causeType);

        rule.setMinAvailabilityThreshold(Math.max(0, availabilityStats.getMean() - availabilityStats.getStandardDeviation()));
        rule.setMaxAvailabilityThreshold(Math.min(100, availabilityStats.getMean() + availabilityStats.getStandardDeviation()));

        rule.setMinLatencyThreshold(Math.max(0, latencyStats.getMean() - latencyStats.getStandardDeviation()));
        rule.setMaxLatencyThreshold(latencyStats.getMean() + latencyStats.getStandardDeviation() * 2);

        rule.setMinErrorRateThreshold(Math.max(0, errorRateStats.getMean() - errorRateStats.getStandardDeviation()));
        rule.setMaxErrorRateThreshold(errorRateStats.getMean() + errorRateStats.getStandardDeviation() * 2);

        rule.setConfidenceScore((int) confidence);
        rule.setSupportCount(analyses.size());
        rule.setHitCount(analyses.size());
        rule.setAutoGenerated(true);
        rule.setActive(true);
        rule.setLastVerifiedAt(LocalDateTime.now());

        rule.setContributingFactors(generateContributingFactors(causeType, availabilityStats, latencyStats, errorRateStats));
        rule.setRecommendations(generateRecommendations(causeType));

        return Optional.of(rule);
    }

    private double calculateConfidence(int supportCount, RootCauseAnalysis.RootCauseCategory causeType) {
        long totalEvents = analysisRepository.count();
        if (totalEvents == 0) return 50.0;

        double support = (double) supportCount / totalEvents;
        double typeWeight = getCauseTypeWeight(causeType);
        
        double confidence = 50 + (support * 500) + typeWeight;
        return Math.min(95, Math.max(50, confidence));
    }

    private double getCauseTypeWeight(RootCauseAnalysis.RootCauseCategory causeType) {
        return switch (causeType) {
            case HIGH_ERROR_RATE -> 10;
            case LATENCY_SPIKE -> 8;
            case TRAFFIC_SURGE -> 5;
            case DEPENDENCY_FAILURE -> 12;
            case RESOURCE_EXHAUSTION -> 10;
            default -> 0;
        };
    }

    private String generateRuleCode(RootCauseAnalysis.RootCauseCategory causeType) {
        return "AUTO_" + causeType + "_" + System.currentTimeMillis() % 10000;
    }

    private String generateRuleName(RootCauseAnalysis.RootCauseCategory causeType) {
        return "自动挖掘规则 - " + getCauseTypeDisplayName(causeType);
    }

    private String getCauseTypeDisplayName(RootCauseAnalysis.RootCauseCategory causeType) {
        return switch (causeType) {
            case HIGH_ERROR_RATE -> "高错误率";
            case LATENCY_SPIKE -> "延迟突增";
            case TRAFFIC_SURGE -> "流量暴增";
            case DEPENDENCY_FAILURE -> "依赖服务故障";
            case RESOURCE_EXHAUSTION -> "资源耗尽";
            default -> "未知原因";
        };
    }

    private String generateContributingFactors(RootCauseAnalysis.RootCauseCategory causeType,
                                                 DescriptiveStatistics availability,
                                                 DescriptiveStatistics latency,
                                                 DescriptiveStatistics errorRate) {
        List<String> factors = new ArrayList<>();

        if (availability.getMean() < 99.9) {
            factors.add("平均可用性低于目标: " + String.format("%.2f", availability.getMean()) + "%");
        }
        if (latency.getMean() > 500) {
            factors.add("平均延迟较高: " + String.format("%.0f", latency.getMean()) + "ms");
        }
        if (errorRate.getMean() > 1.0) {
            factors.add("平均错误率较高: " + String.format("%.2f", errorRate.getMean()) + "%");
        }

        if (factors.isEmpty()) {
            factors.add("基于历史故障模式自动识别的" + getCauseTypeDisplayName(causeType) + "模式");
        }

        return String.join(" | ", factors);
    }

    private String generateRecommendations(RootCauseAnalysis.RootCauseCategory causeType) {
        List<String> recommendations = new ArrayList<>();

        recommendations.addAll(switch (causeType) {
            case HIGH_ERROR_RATE -> Arrays.asList(
                    "检查近期代码变更和部署记录",
                    "分析错误日志中的异常模式",
                    "验证下游依赖服务健康状态",
                    "考虑增加熔断和降级机制"
            );
            case LATENCY_SPIKE -> Arrays.asList(
                    "分析数据库查询性能和索引",
                    "检查缓存命中率",
                    "考虑异步处理非关键路径",
                    "评估是否需要水平扩展"
            );
            case TRAFFIC_SURGE -> Arrays.asList(
                    "检查流量来源是否正常",
                    "考虑限流和降级策略",
                    "验证自动扩容是否正常工作",
                    "检查是否有恶意攻击或爬虫"
            );
            case DEPENDENCY_FAILURE -> Arrays.asList(
                    "检查依赖服务的健康状态",
                    "增加超时和重试机制",
                    "考虑实现熔断机制",
                    "评估关键路径的依赖冗余"
            );
            case RESOURCE_EXHAUSTION -> Arrays.asList(
                    "检查CPU、内存、磁盘使用情况",
                    "分析连接池和线程池配置",
                    "考虑资源扩容",
                    "优化资源释放逻辑"
            );
            default -> Arrays.asList(
                    "进行详细的性能分析",
                    "收集更多诊断信息",
                    "联系运维团队协助排查"
            );
        });

        return String.join(" | ", recommendations);
    }

    public void updateRuleStatistics() {
        List<RootCauseRule> rules = ruleRepository.findByActiveTrue();
        LocalDateTime verificationTime = LocalDateTime.now();

        for (RootCauseRule rule : rules) {
            rule.setLastVerifiedAt(verificationTime);
            rule.updatePrecision();
            ruleRepository.save(rule);
        }

        logger.info("Updated statistics for {} rules", rules.size());
    }

    public List<RootCauseRule> matchRules(Double availability, Double latency, Double errorRate) {
        List<RootCauseRule> matchedRules = ruleRepository.findMatchingRules(
                availability, latency, errorRate);

        for (RootCauseRule rule : matchedRules) {
            rule.incrementHitCount();
            ruleRepository.save(rule);
        }

        return matchedRules;
    }

    public void initializeDefaultRules() {
        if (ruleRepository.count() == 0) {
            logger.info("Initializing default root cause rules...");

            createManualRule(
                    "MANUAL_HIGH_ERROR",
                    "高错误率检测规则",
                    RootCauseAnalysis.RootCauseCategory.HIGH_ERROR_RATE,
                    null, 99.0,
                    null, null,
                    2.0, 100.0,
                    80,
                    "错误率持续高于2%，可用性低于99%",
                    "检查近期部署 | 分析错误日志 | 验证下游服务",
                    "回滚近期变更 | 增加熔断机制 | 联系开发团队排查"
            );

            createManualRule(
                    "MANUAL_LATENCY_SPIKE",
                    "延迟突增检测规则",
                    RootCauseAnalysis.RootCauseCategory.LATENCY_SPIKE,
                    null, null,
                    1000.0, null,
                    null, null,
                    75,
                    "平均延迟超过1000ms",
                    "数据库查询慢 | 缓存命中率低 | 网络延迟高",
                    "优化SQL查询 | 增加缓存层 | 检查网络状况"
            );

            createManualRule(
                    "MANUAL_TRAFFIC_SURGE",
                    "流量暴增检测规则",
                    RootCauseAnalysis.RootCauseCategory.TRAFFIC_SURGE,
                    null, null,
                    null, null,
                    null, null,
                    70,
                    "请求量在短时间内增长超过50%",
                    "流量异常增长 | 可能的促销活动或爬虫",
                    "启用限流 | 检查流量来源 | 自动扩容"
            );

            createManualRule(
                    "MANUAL_DEPENDENCY_FAIL",
                    "依赖服务故障规则",
                    RootCauseAnalysis.RootCauseCategory.DEPENDENCY_FAILURE,
                    null, 95.0,
                    500.0, null,
                    5.0, 100.0,
                    90,
                    "可用性低、延迟高、错误率高同时发生",
                    "下游服务超时 | 连接池耗尽 | 网络分区",
                    "熔断降级 | 检查依赖服务 | 考虑冗余设计"
            );

            logger.info("Default root cause rules initialized");
        }
    }

    private void createManualRule(String code, String name,
                                   RootCauseAnalysis.RootCauseCategory causeType,
                                   Double minAvail, Double maxAvail,
                                   Double minLatency, Double maxLatency,
                                   Double minError, Double maxError,
                                   int confidence,
                                   String description,
                                   String factors,
                                   String recommendations) {
        RootCauseRule rule = new RootCauseRule();
        rule.setRuleCode(code);
        rule.setRuleName(name);
        rule.setRootCauseType(causeType);
        rule.setMinAvailabilityThreshold(minAvail);
        rule.setMaxAvailabilityThreshold(maxAvail);
        rule.setMinLatencyThreshold(minLatency);
        rule.setMaxLatencyThreshold(maxLatency);
        rule.setMinErrorRateThreshold(minError);
        rule.setMaxErrorRateThreshold(maxError);
        rule.setConfidenceScore(confidence);
        rule.setDescription(description);
        rule.setContributingFactors(factors);
        rule.setRecommendations(recommendations);
        rule.setAutoGenerated(false);
        rule.setActive(true);
        ruleRepository.save(rule);
    }
}
