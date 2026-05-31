package com.drill.platform.recommendation;

import com.drill.platform.model.*;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Component
public class StrategyRecommendationEngine {

    public StrategyRecommendation generateRecommendation(
            String targetSystem,
            List<RateLimitStrategy> availableStrategies,
            List<DrillTask> historicalDrills) {
        
        StrategyRecommendation recommendation = new StrategyRecommendation();
        recommendation.setId(UUID.randomUUID().toString());
        recommendation.setTargetSystem(targetSystem);
        recommendation.setGenerateTime(new Date());
        
        Map<String, List<DrillTask>> drillsByStrategy = historicalDrills.stream()
                .filter(d -> d.getStrategyId() != null && d.getResult() != null)
                .collect(Collectors.groupingBy(DrillTask::getStrategyId));
        
        List<StrategyRecommendation.StrategyPerformance> performances = new ArrayList<>();
        
        for (RateLimitStrategy strategy : availableStrategies) {
            List<DrillTask> strategyDrills = drillsByStrategy.getOrDefault(strategy.getId(), Collections.emptyList());
            
            if (!strategyDrills.isEmpty()) {
                StrategyRecommendation.StrategyPerformance performance = calculatePerformance(strategy, strategyDrills);
                performances.add(performance);
            }
        }
        
        performances.sort((a, b) -> Double.compare(b.getAvgScore(), a.getAvgScore()));
        
        recommendation.setHistoricalPerformance(performances);
        
        if (!performances.isEmpty()) {
            StrategyRecommendation.StrategyPerformance bestPerformance = performances.get(0);
            RateLimitStrategy bestStrategy = availableStrategies.stream()
                    .filter(s -> s.getId().equals(bestPerformance.getStrategyId()))
                    .findFirst()
                    .orElse(null);
            
            if (bestStrategy != null) {
                recommendation.setRecommendedStrategy(bestStrategy);
                recommendation.setConfidenceScore(calculateConfidence(bestPerformance, performances));
                recommendation.setRecommendationReason(generateReason(bestPerformance, performances));
            }
        }
        
        if (performances.size() > 1) {
            List<RateLimitStrategy> alternatives = performances.stream()
                    .skip(1)
                    .limit(3)
                    .map(p -> availableStrategies.stream()
                            .filter(s -> s.getId().equals(p.getStrategyId()))
                            .findFirst()
                            .orElse(null))
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());
            recommendation.setAlternativeStrategies(alternatives);
        }
        
        if (historicalDrills.size() > 5) {
            analyzeScenarioCharacteristics(recommendation, historicalDrills);
        }
        
        return recommendation;
    }
    
    private StrategyRecommendation.StrategyPerformance calculatePerformance(
            RateLimitStrategy strategy, List<DrillTask> drills) {
        
        StrategyRecommendation.StrategyPerformance performance = new StrategyRecommendation.StrategyPerformance();
        performance.setStrategyId(strategy.getId());
        performance.setStrategyName(strategy.getName());
        performance.setDrillCount(drills.size());
        
        List<DrillResult> results = drills.stream()
                .map(DrillTask::getResult)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
        
        if (!results.isEmpty()) {
            performance.setAvgScore(results.stream().mapToDouble(DrillResult::getScore).average().orElse(0));
            performance.setBestScore(results.stream().mapToDouble(DrillResult::getScore).max().orElse(0));
            performance.setWorstScore(results.stream().mapToDouble(DrillResult::getScore).min().orElse(0));
            performance.setAvgRecoveryTimeMs(results.stream().mapToDouble(r -> r.getRecoveryTimeMs() != null ? r.getRecoveryTimeMs() : 0).average().orElse(0));
            performance.setAvgErrorRate(results.stream().mapToDouble(DrillResult::getErrorRate).average().orElse(0));
            performance.setPeakQpsHandled(results.stream().mapToDouble(DrillResult::getActualQps).max().orElse(0));
            
            drills.stream()
                    .map(DrillTask::getEndTime)
                    .filter(Objects::nonNull)
                    .max(Date::compareTo)
                    .ifPresent(performance::setLastTestTime);
        }
        
        return performance;
    }
    
    private Double calculateConfidence(
            StrategyRecommendation.StrategyPerformance best,
            List<StrategyRecommendation.StrategyPerformance> all) {
        
        if (all.size() < 2) {
            return best.getDrillCount() >= 3 ? 0.8 : 0.5;
        }
        
        double avgOfOthers = all.stream()
                .skip(1)
                .mapToDouble(StrategyRecommendation.StrategyPerformance::getAvgScore)
                .average()
                .orElse(0);
        
        double scoreGap = best.getAvgScore() - avgOfOthers;
        double countFactor = Math.min(best.getDrillCount() / 5.0, 1.0);
        
        double confidence = 0.5 + (scoreGap / 20.0) * 0.3 + countFactor * 0.2;
        return Math.min(Math.max(confidence, 0.3), 0.95);
    }
    
    private String generateReason(
            StrategyRecommendation.StrategyPerformance best,
            List<StrategyRecommendation.StrategyPerformance> all) {
        
        StringBuilder reason = new StringBuilder();
        reason.append(String.format("策略 '%s' 在 %d 次演练中平均得分 %.1f",
                best.getStrategyName(), best.getDrillCount(), best.getAvgScore()));
        
        if (all.size() > 1) {
            StrategyRecommendation.StrategyPerformance second = all.get(1);
            double improvement = best.getAvgScore() - second.getAvgScore();
            if (improvement > 5) {
                reason.append(String.format("，比次优策略 '%s' 高出 %.1f 分",
                        second.getStrategyName(), improvement));
            }
        }
        
        if (best.getAvgErrorRate() < 2) {
            reason.append("，错误率控制优秀");
        }
        if (best.getAvgRecoveryTimeMs() != null && best.getAvgRecoveryTimeMs() < 5000) {
            reason.append("，恢复速度快");
        }
        
        return reason.toString();
    }
    
    private void analyzeScenarioCharacteristics(
            StrategyRecommendation recommendation,
            List<DrillTask> historicalDrills) {
        
        Map<String, Object> metrics = new HashMap<>();
        
        long spikeCount = historicalDrills.stream()
                .filter(d -> d.getTrafficProfile() != null && "SPIKE".equals(d.getTrafficProfile().getPattern()))
                .count();
        
        long rampCount = historicalDrills.stream()
                .filter(d -> d.getTrafficProfile() != null && 
                        ("LINEAR_RAMP".equals(d.getTrafficProfile().getPattern()) ||
                         "EXPONENTIAL_RAMP".equals(d.getTrafficProfile().getPattern())))
                .count();
        
        String scenarioType;
        if (spikeCount > historicalDrills.size() * 0.5) {
            scenarioType = "SPIKE_PRONE";
        } else if (rampCount > historicalDrills.size() * 0.5) {
            scenarioType = "GRADUAL_GROWTH";
        } else {
            scenarioType = "MIXED";
        }
        
        recommendation.setScenarioType(scenarioType);
        metrics.put("spikeDrillCount", spikeCount);
        metrics.put("rampDrillCount", rampCount);
        metrics.put("totalDrillCount", historicalDrills.size());
        recommendation.setMetrics(metrics);
    }
    
    public List<RateLimitStrategy> generateStrategyVariants(RateLimitStrategy baseStrategy) {
        List<RateLimitStrategy> variants = new ArrayList<>();
        
        int[] thresholds = {
                (int) (baseStrategy.getThreshold() * 0.5),
                (int) (baseStrategy.getThreshold() * 0.75),
                baseStrategy.getThreshold(),
                (int) (baseStrategy.getThreshold() * 1.25),
                (int) (baseStrategy.getThreshold() * 1.5)
        };
        
        for (int i = 0; i < thresholds.length; i++) {
            RateLimitStrategy variant = new RateLimitStrategy();
            variant.setId(UUID.randomUUID().toString());
            variant.setName(baseStrategy.getName() + " - 阈值" + thresholds[i]);
            variant.setType(baseStrategy.getType());
            variant.setThreshold(thresholds[i]);
            variant.setTimeoutMs(baseStrategy.getTimeoutMs());
            variant.setDescription(String.format("基于基准策略生成的变体，阈值调整为%d QPS", thresholds[i]));
            variants.add(variant);
        }
        
        return variants;
    }
}
