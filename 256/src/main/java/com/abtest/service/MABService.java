package com.abtest.service;

import com.abtest.entity.Experiment;
import com.abtest.entity.Metric;
import com.abtest.entity.Variant;
import com.abtest.repository.ExperimentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.math3.distribution.BetaDistribution;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class MABService {

    private static final long REPORT_DELAY_MINUTES = 60;

    private final ExperimentRepository experimentRepository;
    private final ClickHouseMetricsService metricsService;
    private final StatisticsService statisticsService;
    private final BucketingService bucketingService;

    @Transactional
    public void updateTrafficAllocation(Long experimentId) {
        Experiment experiment = experimentRepository.findById(experimentId)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + experimentId));

        if (experiment.getStatus() != Experiment.ExperimentStatus.RUNNING) {
            return;
        }

        if (experiment.getTrafficMode() == Experiment.TrafficAllocationMode.FIXED) {
            return;
        }

        Map<String, Map<String, Object>> variantStats = calculateVariantStats(experiment);
        if (variantStats.isEmpty()) {
            return;
        }

        Map<String, Integer> newWeights = switch (experiment.getTrafficMode()) {
            case THOMPSON_SAMPLING -> thompsonSampling(experiment, variantStats);
            case EPSILON_GREEDY -> epsilonGreedy(experiment, variantStats);
            case UCB -> upperConfidenceBound(experiment, variantStats);
            default -> null;
        };

        if (newWeights != null) {
            applyNewWeights(experiment, newWeights);
        }
    }

    private Map<String, Map<String, Object>> calculateVariantStats(Experiment experiment) {
        Map<String, Map<String, Object>> stats = new HashMap<>();
        Metric primaryMetric = experiment.getMetrics().get(0);

        for (Variant variant : experiment.getVariants()) {
            Map<String, Object> metricStats = metricsService.calculateMetric(
                experiment.getId(), variant.getName(), primaryMetric, REPORT_DELAY_MINUTES);
            if (!metricStats.containsKey("error")) {
                stats.put(variant.getName(), metricStats);
            }
        }

        return stats;
    }

    private Map<String, Integer> thompsonSampling(Experiment experiment,
                                                   Map<String, Map<String, Object>> variantStats) {
        Map<String, Integer> weights = new HashMap<>();
        int numSamples = 1000;
        Map<String, Integer> winCounts = new HashMap<>();

        for (String variantName : variantStats.keySet()) {
            winCounts.put(variantName, 0);
        }

        for (int i = 0; i < numSamples; i++) {
            String bestVariant = null;
            double bestSample = -1;

            for (Map.Entry<String, Map<String, Object>> entry : variantStats.entrySet()) {
                Map<String, Object> stats = entry.getValue();
                double sample;

                if (stats.containsKey("conversionRate")) {
                    int conversions = ((Number) stats.getOrDefault("convertedUsers", 0)).intValue();
                    int total = ((Number) stats.getOrDefault("totalUsers", 0)).intValue();
                    int failures = total - conversions;
                    BetaDistribution beta = new BetaDistribution(conversions + 1, failures + 1);
                    sample = beta.sample();
                } else {
                    double mean = ((Number) stats.getOrDefault("avgValue", 0)).doubleValue();
                    double std = ((Number) stats.getOrDefault("stddevValue", 0.1)).doubleValue();
                    int n = ((Number) stats.getOrDefault("userCount", 100)).intValue();
                    double se = std / Math.sqrt(n);
                    sample = mean + new Random().nextGaussian() * se;
                }

                if (sample > bestSample) {
                    bestSample = sample;
                    bestVariant = entry.getKey();
                }
            }

            if (bestVariant != null) {
                winCounts.merge(bestVariant, 1, Integer::sum);
            }
        }

        int totalWins = winCounts.values().stream().mapToInt(Integer::intValue).sum();
        for (Map.Entry<String, Integer> entry : winCounts.entrySet()) {
            double proportion = (double) entry.getValue() / totalWins;
            int weight = (int) Math.max(proportion * 100, 5);
            weights.put(entry.getKey(), weight);
        }

        return weights;
    }

    private Map<String, Integer> epsilonGreedy(Experiment experiment,
                                                Map<String, Map<String, Object>> variantStats) {
        Map<String, Integer> weights = new HashMap<>();
        double epsilon = experiment.getMabEpsilon() != null ? experiment.getMabEpsilon() : 0.1;

        String bestVariant = findBestVariant(variantStats);
        int numVariants = variantStats.size();

        for (String variantName : variantStats.keySet()) {
            if (variantName.equals(bestVariant)) {
                weights.put(variantName, (int) ((1 - epsilon) * 100));
            } else {
                weights.put(variantName, (int) (epsilon * 100 / (numVariants - 1)));
            }
        }

        return weights;
    }

    private Map<String, Integer> upperConfidenceBound(Experiment experiment,
                                                       Map<String, Map<String, Object>> variantStats) {
        Map<String, Integer> weights = new HashMap<>();
        Map<String, Double> ucbScores = new HashMap<>();

        int totalImpressions = variantStats.values().stream()
            .mapToInt(stats -> ((Number) stats.getOrDefault("userCount", 0)).intValue())
            .sum();

        for (Map.Entry<String, Map<String, Object>> entry : variantStats.entrySet()) {
            Map<String, Object> stats = entry.getValue();
            double mean;
            int n;

            if (stats.containsKey("conversionRate")) {
                mean = ((Number) stats.get("conversionRate")).doubleValue();
                n = ((Number) stats.getOrDefault("totalUsers", 0)).intValue();
            } else {
                mean = ((Number) stats.getOrDefault("avgValue", 0)).doubleValue();
                n = ((Number) stats.getOrDefault("userCount", 0)).intValue();
            }

            if (n == 0) {
                ucbScores.put(entry.getKey(), Double.MAX_VALUE);
            } else {
                double exploration = Math.sqrt(2 * Math.log(totalImpressions) / n);
                ucbScores.put(entry.getKey(), mean + exploration);
            }
        }

        double totalScore = ucbScores.values().stream().mapToDouble(Double::doubleValue).sum();
        for (Map.Entry<String, Double> entry : ucbScores.entrySet()) {
            double proportion = entry.getValue() / totalScore;
            weights.put(entry.getKey(), (int) Math.max(proportion * 100, 5));
        }

        return weights;
    }

    private String findBestVariant(Map<String, Map<String, Object>> variantStats) {
        String bestVariant = null;
        double bestValue = -1;

        for (Map.Entry<String, Map<String, Object>> entry : variantStats.entrySet()) {
            Map<String, Object> stats = entry.getValue();
            double value;

            if (stats.containsKey("conversionRate")) {
                value = ((Number) stats.get("conversionRate")).doubleValue();
            } else {
                value = ((Number) stats.getOrDefault("avgValue", 0)).doubleValue();
            }

            if (value > bestValue) {
                bestValue = value;
                bestVariant = entry.getKey();
            }
        }

        return bestVariant;
    }

    private void applyNewWeights(Experiment experiment, Map<String, Integer> newWeights) {
        for (Variant variant : experiment.getVariants()) {
            Integer newWeight = newWeights.get(variant.getName());
            if (newWeight != null) {
                variant.setTrafficWeight(newWeight);
            }
        }

        experiment.setLastTrafficAdjustmentTime(LocalDateTime.now());
        experimentRepository.save(experiment);

        bucketingService.clearBucketCache(experiment.getId());
        bucketingService.refreshHashRing(experiment.getId());

        log.info("Updated MAB traffic allocation for experiment {}: {}",
            experiment.getId(), newWeights);
    }

    public Map<String, Object> getMABStatus(Long experimentId) {
        Experiment experiment = experimentRepository.findById(experimentId)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + experimentId));

        Map<String, Object> status = new LinkedHashMap<>();
        status.put("experimentId", experimentId);
        status.put("trafficMode", experiment.getTrafficMode());
        status.put("lastTrafficAdjustmentTime", experiment.getLastTrafficAdjustmentTime());
        status.put("mabEpsilon", experiment.getMabEpsilon());
        status.put("mabUpdateIntervalMinutes", experiment.getMabUpdateIntervalMinutes());

        Map<String, Integer> currentWeights = experiment.getVariants().stream()
            .collect(Collectors.toMap(Variant::getName, Variant::getTrafficWeight));
        status.put("currentWeights", currentWeights);

        Map<String, Map<String, Object>> variantStats = calculateVariantStats(experiment);
        status.put("variantStats", variantStats);

        return status;
    }

    public boolean shouldUpdateTraffic(Experiment experiment) {
        if (experiment.getTrafficMode() == Experiment.TrafficAllocationMode.FIXED) {
            return false;
        }

        if (experiment.getLastTrafficAdjustmentTime() == null) {
            return true;
        }

        int interval = experiment.getMabUpdateIntervalMinutes() != null
            ? experiment.getMabUpdateIntervalMinutes()
            : 60;

        return experiment.getLastTrafficAdjustmentTime()
            .plusMinutes(interval)
            .isBefore(LocalDateTime.now());
    }
}
