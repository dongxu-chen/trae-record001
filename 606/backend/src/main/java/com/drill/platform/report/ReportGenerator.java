package com.drill.platform.report;

import com.drill.platform.model.*;
import com.drill.platform.scoring.ScoringEngine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Date;
import java.util.UUID;

@Component
@Slf4j
public class ReportGenerator {

    private final ScoringEngine scoringEngine;

    public ReportGenerator(ScoringEngine scoringEngine) {
        this.scoringEngine = scoringEngine;
    }

    public DrillReport generate(DrillTask task, RateLimitStrategy strategy) {
        DrillResult result = task.getResult();
        if (result == null) {
            log.warn("Cannot generate report for task without result: {}", task.getId());
            return null;
        }

        scoringEngine.calculateScore(result, strategy);

        DrillReport report = new DrillReport();
        report.setId(UUID.randomUUID().toString());
        report.setTaskId(task.getId());
        report.setTaskName(task.getName());
        report.setGenerateTime(new Date());
        report.setTrafficProfile(task.getTrafficProfile());
        report.setStrategy(strategy);
        report.setResult(result);
        report.setConclusion(generateConclusion(result, strategy));
        report.setRecommendation(generateRecommendation(result, strategy));

        log.info("Generated report for task: {}, score: {}", task.getId(), result.getScore());
        return report;
    }

    private String generateConclusion(DrillResult result, RateLimitStrategy strategy) {
        StringBuilder sb = new StringBuilder();
        double score = result.getScore();

        sb.append("系统综合评分：").append(String.format("%.1f", score)).append("/100。");

        if (score >= 90) {
            sb.append("系统在当前限流降级策略下表现优秀，");
        } else if (score >= 75) {
            sb.append("系统在当前限流降级策略下表现良好，");
        } else if (score >= 60) {
            sb.append("系统在当前限流降级策略下表现一般，");
        } else {
            sb.append("系统在当前限流降级策略下表现较差，");
        }

        sb.append("限流策略：").append(strategy.getType().name());
        sb.append("，阈值：").append(strategy.getThreshold());
        sb.append("，实际QPS：").append(String.format("%.1f", result.getActualQps()));
        sb.append("，拦截率：").append(String.format("%.1f%%", result.getBlockRate()));
        sb.append("，错误率：").append(String.format("%.1f%%", result.getErrorRate()));
        sb.append("，峰值错误率：").append(String.format("%.1f%%", result.getPeakErrorRate()));
        sb.append("，P95响应时间：").append(result.getP95ResponseTimeMs()).append("ms");
        if (result.getRecoveryTimeMs() > 0) {
            sb.append("，恢复时间：").append(result.getRecoveryTimeMs()).append("ms");
        }
        sb.append("，错误抖动：").append(String.format("%.2f", result.getErrorRateJitter()));

        return sb.toString();
    }

    private String generateRecommendation(DrillResult result, RateLimitStrategy strategy) {
        StringBuilder sb = new StringBuilder();

        if (result.getErrorRate() > 10) {
            sb.append("错误率过高(").append(String.format("%.1f%%", result.getErrorRate()))
              .append(")，建议检查服务健康状态和资源容量；");
        }

        if (result.getP95ResponseTimeMs() > 1000) {
            sb.append("P95响应时间过长(").append(result.getP95ResponseTimeMs())
              .append("ms)，建议优化慢接口或增加降级策略；");
        }

        if (result.getBlockRate() > 50) {
            sb.append("限流拦截率过高(").append(String.format("%.1f%%", result.getBlockRate()))
              .append(")，建议适当提高限流阈值或增加服务容量；");
        }

        if (result.getBlockRate() < 5 && result.getErrorRate() > 5) {
            sb.append("限流拦截率低但错误率高，建议降低限流阈值以保护系统；");
        }

        if (strategy.getType() == RateLimitStrategy.StrategyType.DIRECT_REJECT && result.getBlockRate() > 30) {
            sb.append("直接拒绝模式下拦截率高，建议考虑切换为预热(WARM_UP)或排队等待(RATE_LIMITER)模式；");
        }

        if (result.getDegradationRate() < 5 && result.getErrorRate() > 10) {
            sb.append("降级触发率低但错误率高，建议调整熔断降级阈值以提高保护效果；");
        }

        if (result.getRecoveryTimeMs() > 5000) {
            sb.append("系统恢复时间过长(").append(result.getRecoveryTimeMs())
              .append("ms)，建议优化自动恢复机制，缩短熔断恢复时间；");
        }

        if (result.getErrorRateJitter() > 5) {
            sb.append("错误率抖动过大(").append(String.format("%.2f", result.getErrorRateJitter()))
              .append(")，系统稳定性欠佳，建议排查资源瓶颈或依赖服务；");
        }

        if (result.getOverThresholdSeconds() > 10) {
            sb.append("超阈值持续时间过长(").append(result.getOverThresholdSeconds())
              .append("秒)，建议优化限流策略响应速度，降低系统暴露风险；");
        }

        if (result.getPeakErrorRate() - result.getErrorRate() > 20) {
            sb.append("峰值错误率与平均错误率差距过大(")
              .append(String.format("%.1f%%", result.getPeakErrorRate() - result.getErrorRate()))
              .append(")，建议加强峰值流量防护；");
        }

        if (!result.isAutoRecovered() && result.getErrorRate() > 10) {
            sb.append("系统未实现自动恢复，建议配置合理的熔断降级策略实现故障自愈；");
        }

        if (sb.length() == 0) {
            sb.append("当前策略配置合理，系统表现稳定，建议持续监控并定期演练。");
        }

        return sb.toString();
    }
}
