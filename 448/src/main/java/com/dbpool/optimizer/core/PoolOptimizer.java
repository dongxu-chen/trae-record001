package com.dbpool.optimizer.core;

import com.dbpool.optimizer.model.*;
import org.springframework.stereotype.Component;
import java.util.*;

@Component
public class PoolOptimizer {

    private final QueueingTheoryAnalyzer queueingAnalyzer;
    private final ConnectionPoolSimulator simulator;

    public PoolOptimizer(QueueingTheoryAnalyzer queueingAnalyzer,
                         ConnectionPoolSimulator simulator) {
        this.queueingAnalyzer = queueingAnalyzer;
        this.simulator = simulator;
    }

    public OptimizationRecommendation optimize(OptimizationRequest request) {
        PoolConfig currentConfig = request.getCurrentConfig();
        WorkloadProfile workload = request.getWorkload();
        DatabaseConstraint dbConstraint = request.getDatabaseConstraint();

        int optimalPoolSize = calculateOptimalPoolSize(request);
        if (dbConstraint != null) {
            optimalPoolSize = enforceDatabaseConstraint(optimalPoolSize, dbConstraint);
        }

        int optimalMinIdle = calculateOptimalMinIdle(optimalPoolSize, workload);
        long optimalConnectionTimeout = calculateOptimalConnectionTimeout(workload);
        long optimalIdleTimeout = calculateOptimalIdleTimeout(workload);
        long optimalMaxLifetime = calculateOptimalMaxLifetime(workload);
        long optimalLeakDetection = calculateOptimalLeakDetection(workload);

        PoolConfig optimizedConfig = PoolConfig.builder()
                .poolType(currentConfig.getPoolType())
                .maxPoolSize(optimalPoolSize)
                .minIdle(optimalMinIdle)
                .connectionTimeoutMs(optimalConnectionTimeout)
                .idleTimeoutMs(optimalIdleTimeout)
                .maxLifetimeMs(optimalMaxLifetime)
                .leakDetectionThresholdMs(optimalLeakDetection)
                .validationQuery(currentConfig.getValidationQuery())
                .testOnBorrow(currentConfig.isTestOnBorrow())
                .testOnReturn(currentConfig.isTestOnReturn())
                .testWhileIdle(true)
                .timeBetweenEvictionRunsMs(30000)
                .numTestsPerEvictionRun(Math.min(optimalPoolSize / 3, 5))
                .build();

        SimulationResult optimizedResult = simulator.simulate(optimizedConfig, workload);

        List<String> recommendations = generateRecommendations(currentConfig, optimizedConfig, workload, dbConstraint);
        Map<String, String> configChanges = generateConfigChanges(currentConfig, optimizedConfig);
        double resourceSavingPercent = calculateResourceSaving(currentConfig, optimizedConfig);
        double throughputImprovement = calculateThroughputImprovement(currentConfig, optimizedConfig, workload);
        String riskLevel = calculateRiskLevel(currentConfig, optimizedConfig, dbConstraint);
        String justification = generateJustification(currentConfig, optimizedConfig, workload, optimizedResult, dbConstraint);

        return OptimizationRecommendation.builder()
                .recommendedMaxPoolSize(optimalPoolSize)
                .recommendedMinIdle(optimalMinIdle)
                .recommendedConnectionTimeoutMs(optimalConnectionTimeout)
                .recommendedIdleTimeoutMs(optimalIdleTimeout)
                .recommendedMaxLifetimeMs(optimalMaxLifetime)
                .recommendedLeakDetectionThresholdMs(optimalLeakDetection)
                .expectedAvgWaitTimeMs(optimizedResult.getAvgWaitTimeMs())
                .expectedUtilization(optimizedResult.getConnectionUtilization())
                .expectedThroughputImprovement(throughputImprovement)
                .resourceSavingPercent(resourceSavingPercent)
                .recommendations(recommendations)
                .configurationChanges(configChanges)
                .riskLevel(riskLevel)
                .justification(justification)
                .build();
    }

    public ConfigComparison compareAndOptimize(OptimizationRequest request) {
        PoolConfig originalConfig = request.getCurrentConfig();
        WorkloadProfile workload = request.getWorkload();

        SimulationResult originalResult = simulator.simulate(originalConfig, workload);
        OptimizationRecommendation recommendation = optimize(request);

        PoolConfig optimizedConfig = PoolConfig.builder()
                .poolType(originalConfig.getPoolType())
                .maxPoolSize(recommendation.getRecommendedMaxPoolSize())
                .minIdle(recommendation.getRecommendedMinIdle())
                .connectionTimeoutMs(recommendation.getRecommendedConnectionTimeoutMs())
                .idleTimeoutMs(recommendation.getRecommendedIdleTimeoutMs())
                .maxLifetimeMs(recommendation.getRecommendedMaxLifetimeMs())
                .leakDetectionThresholdMs(recommendation.getRecommendedLeakDetectionThresholdMs())
                .validationQuery(originalConfig.getValidationQuery())
                .testOnBorrow(originalConfig.isTestOnBorrow())
                .testOnReturn(originalConfig.isTestOnReturn())
                .testWhileIdle(true)
                .timeBetweenEvictionRunsMs(30000)
                .numTestsPerEvictionRun(5)
                .build();

        SimulationResult optimizedResult = simulator.simulate(optimizedConfig, workload);
        Map<String, Double> improvements = calculateImprovements(originalResult, optimizedResult);
        String summary = generateComparisonSummary(originalResult, optimizedResult, improvements);

        return ConfigComparison.builder()
                .originalConfig(originalConfig)
                .optimizedConfig(optimizedConfig)
                .originalResult(originalResult)
                .optimizedResult(optimizedResult)
                .improvements(improvements)
                .summary(summary)
                .build();
    }

    private int enforceDatabaseConstraint(int optimalPoolSize, DatabaseConstraint constraint) {
        int availableConnections = constraint.getAvailableConnections();
        if (optimalPoolSize > availableConnections) {
            return availableConnections;
        }
        return optimalPoolSize;
    }

    private int calculateOptimalPoolSize(OptimizationRequest request) {
        WorkloadProfile workload = request.getWorkload();
        double targetWaitTime = request.getTargetWaitTimeMs();
        double maxAllowedUtilization = request.getMaxAllowedUtilization();

        double requiredServersByWaitTime;
        if (request.getDatabaseConstraint() != null) {
            requiredServersByWaitTime = queueingAnalyzer.calculateRequiredServersWithConstraint(
                    targetWaitTime, workload, request.getDatabaseConstraint());
        } else {
            requiredServersByWaitTime = queueingAnalyzer.calculateRequiredServers(targetWaitTime, workload);
        }

        double arrivalRate = workload.getArrivalRate();
        double effectiveAvgServiceTime = workload.getAvgServiceTimeMs();

        if (workload.getMixedTransactionConfig() != null && workload.getMixedTransactionConfig().isEnabled()) {
            MixedTransactionConfig mtc = workload.getMixedTransactionConfig();
            effectiveAvgServiceTime = mtc.getShortQueryRatio() * mtc.getShortQueryAvgTimeMs()
                    + (1 - mtc.getShortQueryRatio()) * mtc.getLongQueryAvgTimeMs();
        }

        double serviceRate = 1000.0 / effectiveAvgServiceTime;
        double requiredServersByUtilization = (arrivalRate / serviceRate) / maxAllowedUtilization;
        double peakServers = workload.getPeakConcurrentUsers() * 0.8;

        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            double burstiness = workload.getMarkovArrivalConfig().getBurstinessFactor();
            peakServers *= (1 + (burstiness - 1) * 0.3);
        }

        int optimalSize = (int) Math.ceil(Math.max(
                requiredServersByWaitTime,
                Math.max(requiredServersByUtilization, peakServers)
        ));

        optimalSize = Math.max(5, Math.min(100, optimalSize));

        return optimalSize;
    }

    private int calculateOptimalMinIdle(int maxPoolSize, WorkloadProfile workload) {
        double avgConcurrentConnections = workload.getArrivalRate() * workload.getAvgServiceTimeMs() / 1000.0;
        int minIdle = (int) Math.ceil(avgConcurrentConnections * 0.5);

        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            double burstiness = workload.getMarkovArrivalConfig().getBurstinessFactor();
            minIdle = (int) Math.ceil(minIdle * (1 + (burstiness - 1) * 0.2));
        }

        minIdle = Math.max(2, Math.min(maxPoolSize / 2, minIdle));
        return minIdle;
    }

    private long calculateOptimalConnectionTimeout(WorkloadProfile workload) {
        double p99ServiceTime;
        if (workload.getMixedTransactionConfig() != null && workload.getMixedTransactionConfig().isEnabled()) {
            MixedTransactionConfig mtc = workload.getMixedTransactionConfig();
            p99ServiceTime = mtc.getLongQueryAvgTimeMs() + 3 * mtc.getLongQueryStdDevMs();
        } else {
            p99ServiceTime = workload.getAvgServiceTimeMs() + 3 * workload.getServiceTimeStdDevMs();
        }
        long timeout = (long) Math.max(30000, p99ServiceTime * 5);
        return Math.min(timeout, 300000);
    }

    private long calculateOptimalIdleTimeout(WorkloadProfile workload) {
        double arrivalRate = workload.getArrivalRate();
        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            return 600000;
        }
        if (arrivalRate > 100) {
            return 600000;
        } else if (arrivalRate > 10) {
            return 300000;
        } else {
            return 60000;
        }
    }

    private long calculateOptimalMaxLifetime(WorkloadProfile workload) {
        return 1800000;
    }

    private long calculateOptimalLeakDetection(WorkloadProfile workload) {
        double p99ServiceTime;
        if (workload.getMixedTransactionConfig() != null && workload.getMixedTransactionConfig().isEnabled()) {
            MixedTransactionConfig mtc = workload.getMixedTransactionConfig();
            p99ServiceTime = mtc.getLongQueryAvgTimeMs() + 3 * mtc.getLongQueryStdDevMs();
        } else {
            p99ServiceTime = workload.getAvgServiceTimeMs() + 3 * workload.getServiceTimeStdDevMs();
        }
        long threshold = (long) (p99ServiceTime * 10);
        return Math.max(threshold, 60000);
    }

    private List<String> generateRecommendations(PoolConfig current, PoolConfig optimized,
                                                  WorkloadProfile workload, DatabaseConstraint dbConstraint) {
        List<String> recommendations = new ArrayList<>();

        if (dbConstraint != null && optimized.getMaxPoolSize() > current.getMaxPoolSize()) {
            int dbLimit = dbConstraint.getAvailableConnections();
            if (optimized.getMaxPoolSize() >= dbLimit) {
                recommendations.add(String.format(
                        "注意：推荐连接数 %d 已达到数据库可用上限 %d（总 %d / 共享应用 %d - 预留 %d），" +
                                "无法继续增加，建议优化查询或升级数据库",
                        optimized.getMaxPoolSize(), dbLimit,
                        dbConstraint.getMaxDatabaseConnections(),
                        dbConstraint.getSharedByApplications(),
                        dbConstraint.getReservedConnections()));
            }
        }

        if (optimized.getMaxPoolSize() < current.getMaxPoolSize()) {
            int reduction = current.getMaxPoolSize() - optimized.getMaxPoolSize();
            recommendations.add(String.format("减少最大连接数从 %d 到 %d，节省 %d 个数据库连接资源",
                    current.getMaxPoolSize(), optimized.getMaxPoolSize(), reduction));
        } else if (optimized.getMaxPoolSize() > current.getMaxPoolSize()) {
            int increase = optimized.getMaxPoolSize() - current.getMaxPoolSize();
            recommendations.add(String.format("增加最大连接数从 %d 到 %d，以支持更高的并发需求",
                    current.getMaxPoolSize(), optimized.getMaxPoolSize()));
        } else {
            recommendations.add("当前最大连接数配置合理，无需调整");
        }

        if (dbConstraint != null && current.getMaxPoolSize() > dbConstraint.getAvailableConnections()) {
            recommendations.add(String.format("警告：当前连接池大小 %d 超过数据库可用连接上限 %d，" +
                            "可能导致数据库连接耗尽！建议立即调整",
                    current.getMaxPoolSize(), dbConstraint.getAvailableConnections()));
        }

        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            double burstiness = workload.getMarkovArrivalConfig().getBurstinessFactor();
            if (burstiness > 1.5) {
                recommendations.add(String.format(
                        "业务具有较强突发性（突发因子 %.1f），建议适当增加最小空闲连接数和连接超时时间，" +
                                "并考虑设置连接池预热策略", burstiness));
            }
        }

        if (workload.getMixedTransactionConfig() != null && workload.getMixedTransactionConfig().isEnabled()) {
            double longRatio = 1 - workload.getMixedTransactionConfig().getShortQueryRatio();
            if (longRatio > 0.3) {
                recommendations.add(String.format(
                        "长查询占比 %.0f%% 较高，建议考虑读写分离或将长查询路由到专用连接池",
                        longRatio * 100));
            }
        }

        if (optimized.getMinIdle() != current.getMinIdle()) {
            recommendations.add(String.format("调整最小空闲连接数从 %d 到 %d，平衡启动性能和资源占用",
                    current.getMinIdle(), optimized.getMinIdle()));
        }

        if (optimized.getConnectionTimeoutMs() != current.getConnectionTimeoutMs()) {
            recommendations.add(String.format("调整连接超时从 %dms 到 %dms，避免请求过长等待",
                    current.getConnectionTimeoutMs(), optimized.getConnectionTimeoutMs()));
        }

        if (!current.isTestWhileIdle()) {
            recommendations.add("启用空闲连接检测（testWhileIdle=true），防止连接失效");
        }

        if (current.getLeakDetectionThresholdMs() <= 0) {
            recommendations.add("启用连接泄漏检测，设置合理的阈值以发现连接泄漏问题");
        }

        if (workload.getPeakConcurrentUsers() > current.getMaxPoolSize()) {
            recommendations.add("警告：峰值并发用户数超过当前连接池容量，可能导致请求排队或超时");
        }

        return recommendations;
    }

    private Map<String, String> generateConfigChanges(PoolConfig current, PoolConfig optimized) {
        Map<String, String> changes = new LinkedHashMap<>();

        if (current.getMaxPoolSize() != optimized.getMaxPoolSize()) {
            changes.put("maxPoolSize", current.getMaxPoolSize() + " -> " + optimized.getMaxPoolSize());
        }
        if (current.getMinIdle() != optimized.getMinIdle()) {
            changes.put("minIdle", current.getMinIdle() + " -> " + optimized.getMinIdle());
        }
        if (current.getConnectionTimeoutMs() != optimized.getConnectionTimeoutMs()) {
            changes.put("connectionTimeoutMs", current.getConnectionTimeoutMs() + " -> " + optimized.getConnectionTimeoutMs());
        }
        if (current.getIdleTimeoutMs() != optimized.getIdleTimeoutMs()) {
            changes.put("idleTimeoutMs", current.getIdleTimeoutMs() + " -> " + optimized.getIdleTimeoutMs());
        }
        if (current.getMaxLifetimeMs() != optimized.getMaxLifetimeMs()) {
            changes.put("maxLifetimeMs", current.getMaxLifetimeMs() + " -> " + optimized.getMaxLifetimeMs());
        }
        if (current.getLeakDetectionThresholdMs() != optimized.getLeakDetectionThresholdMs()) {
            changes.put("leakDetectionThresholdMs", current.getLeakDetectionThresholdMs() + " -> " + optimized.getLeakDetectionThresholdMs());
        }
        if (!current.isTestWhileIdle() && optimized.isTestWhileIdle()) {
            changes.put("testWhileIdle", current.isTestWhileIdle() + " -> " + optimized.isTestWhileIdle());
        }

        return changes;
    }

    private double calculateResourceSaving(PoolConfig current, PoolConfig optimized) {
        if (optimized.getMaxPoolSize() >= current.getMaxPoolSize()) {
            return 0;
        }
        return (double) (current.getMaxPoolSize() - optimized.getMaxPoolSize()) / current.getMaxPoolSize() * 100;
    }

    private double calculateThroughputImprovement(PoolConfig current, PoolConfig optimized, WorkloadProfile workload) {
        QueueMetrics currentMetrics = queueingAnalyzer.analyze(current, workload);
        QueueMetrics optimizedMetrics = queueingAnalyzer.analyze(optimized, workload);

        if (currentMetrics.getAvgQueueWaitTimeMs() <= 0) {
            return 0;
        }
        return (currentMetrics.getAvgQueueWaitTimeMs() - optimizedMetrics.getAvgQueueWaitTimeMs())
                / currentMetrics.getAvgQueueWaitTimeMs() * 100;
    }

    private String calculateRiskLevel(PoolConfig current, PoolConfig optimized, DatabaseConstraint dbConstraint) {
        int sizeDiff = Math.abs(current.getMaxPoolSize() - optimized.getMaxPoolSize());
        double changePercent = (double) sizeDiff / current.getMaxPoolSize();

        if (dbConstraint != null && optimized.getMaxPoolSize() >= dbConstraint.getAvailableConnections() * 0.9) {
            return "HIGH";
        }

        if (changePercent < 0.1) {
            return "LOW";
        } else if (changePercent < 0.3) {
            return "MEDIUM";
        } else {
            return "HIGH";
        }
    }

    private String generateJustification(PoolConfig current, PoolConfig optimized,
                                         WorkloadProfile workload, SimulationResult result,
                                         DatabaseConstraint dbConstraint) {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("基于排队论分析和业务负载模拟（到达率 %.1f req/s，平均服务时间 %.0fms），",
                workload.getArrivalRate(), workload.getAvgServiceTimeMs()));

        if (workload.getMarkovArrivalConfig() != null && workload.getMarkovArrivalConfig().isEnabled()) {
            sb.append(String.format("采用马尔可夫到达过程（MAP）建模，突发因子 %.1f，",
                    workload.getMarkovArrivalConfig().getBurstinessFactor()));
        }

        if (workload.getMixedTransactionConfig() != null && workload.getMixedTransactionConfig().isEnabled()) {
            sb.append(String.format("混合事务模型（短查询占比 %.0f%%），",
                    workload.getMixedTransactionConfig().getShortQueryRatio() * 100));
        }

        sb.append(String.format("推荐连接池配置可达到 %.1f%% 的资源利用率，" +
                        "预期平均等待时间为 %.2fms，P95 等待时间为 %.2fms。",
                result.getConnectionUtilization() * 100,
                result.getAvgWaitTimeMs(),
                result.getPercentile95WaitTimeMs()));

        if (dbConstraint != null) {
            sb.append(String.format(" 数据库连接上限约束：总 %d 连接，%d 应用共享，预留 %d，可用 %d。",
                    dbConstraint.getMaxDatabaseConnections(),
                    dbConstraint.getSharedByApplications(),
                    dbConstraint.getReservedConnections(),
                    dbConstraint.getAvailableConnections()));
        }

        return sb.toString();
    }

    private Map<String, Double> calculateImprovements(SimulationResult original, SimulationResult optimized) {
        Map<String, Double> improvements = new LinkedHashMap<>();

        if (original.getAvgWaitTimeMs() > 0) {
            improvements.put("waitTimeReductionPercent",
                    (original.getAvgWaitTimeMs() - optimized.getAvgWaitTimeMs()) / original.getAvgWaitTimeMs() * 100);
        }
        if (original.getPercentile95WaitTimeMs() > 0) {
            improvements.put("p95WaitTimeReductionPercent",
                    (original.getPercentile95WaitTimeMs() - optimized.getPercentile95WaitTimeMs()) / original.getPercentile95WaitTimeMs() * 100);
        }
        improvements.put("throughputImprovementPercent",
                (optimized.getThroughput() - original.getThroughput()) / Math.max(1, original.getThroughput()) * 100);
        improvements.put("utilizationChangePercent",
                (optimized.getConnectionUtilization() - original.getConnectionUtilization()) * 100);
        improvements.put("resourceSavingPercent",
                (original.getConfig().getMaxPoolSize() - optimized.getConfig().getMaxPoolSize())
                        / (double) original.getConfig().getMaxPoolSize() * 100);

        return improvements;
    }

    private String generateComparisonSummary(SimulationResult original, SimulationResult optimized,
                                             Map<String, Double> improvements) {
        StringBuilder summary = new StringBuilder();
        summary.append("优化前后对比：");

        Double waitTimeReduction = improvements.get("waitTimeReductionPercent");
        if (waitTimeReduction != null && waitTimeReduction > 0) {
            summary.append(String.format("平均等待时间降低 %.1f%% (%.2fms → %.2fms)；",
                    waitTimeReduction, original.getAvgWaitTimeMs(), optimized.getAvgWaitTimeMs()));
        }

        Double resourceSaving = improvements.get("resourceSavingPercent");
        if (resourceSaving != null && resourceSaving > 0) {
            summary.append(String.format("连接资源节省 %.1f%% (%d → %d 个连接)；",
                    resourceSaving, original.getConfig().getMaxPoolSize(), optimized.getConfig().getMaxPoolSize()));
        }

        Double throughputImprovement = improvements.get("throughputImprovementPercent");
        if (throughputImprovement != null && throughputImprovement > 0) {
            summary.append(String.format("系统吞吐量提升 %.1f%%。", throughputImprovement));
        }

        return summary.toString();
    }
}
