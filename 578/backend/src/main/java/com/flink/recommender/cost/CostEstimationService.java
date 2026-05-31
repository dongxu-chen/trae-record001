package com.flink.recommender.cost;

import com.flink.recommender.model.ResourceConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class CostEstimationService {

    private static final Logger logger = LoggerFactory.getLogger(CostEstimationService.class);

    @Value("${recommendation.cost-per-cpu-per-hour:0.05}")
    private double costPerCpuPerHour;

    @Value("${recommendation.cost-per-gb-memory-per-hour:0.02}")
    private double costPerGbMemoryPerHour;

    @Value("${recommendation.cost-per-gb-network-in:0.0}")
    private double costPerGbNetworkIn;

    @Value("${recommendation.cost-per-gb-network-out:0.08}")
    private double costPerGbNetworkOut;

    @Value("${recommendation.cost-per-gb-cross-rack:0.02}")
    private double costPerGbCrossRack;

    @Value("${recommendation.cost-per-gb-cross-az:0.05}")
    private double costPerGbCrossAz;

    public Map<String, Object> calculateJobCost(ResourceConfig config) {
        return calculateJobCost(config, NetworkCostModel.getDefaultModel());
    }

    public Map<String, Object> calculateJobCost(ResourceConfig config, NetworkCostModel networkModel) {
        logger.debug("Calculating cost for configuration: {}", config);

        double totalCpuCores = config.getTaskManagerCpuCores() * config.getNumTaskManagers();
        double totalMemoryGb = (config.getTaskManagerMemoryMb() * config.getNumTaskManagers()) / 1024.0;
        double jmMemoryGb = config.getJobManagerMemoryMb() / 1024.0;

        double tmCpuCostPerHour = totalCpuCores * costPerCpuPerHour;
        double tmMemoryCostPerHour = totalMemoryGb * costPerGbMemoryPerHour;
        double jmMemoryCostPerHour = jmMemoryGb * costPerGbMemoryPerHour;

        Map<String, Object> networkCost = calculateNetworkCost(config, networkModel);
        double networkCostPerHour = (Double) networkCost.get("totalNetworkCostPerHour");

        double totalCostPerHour = tmCpuCostPerHour + tmMemoryCostPerHour + jmMemoryCostPerHour + networkCostPerHour;

        Map<String, Object> costBreakdown = new HashMap<>();

        costBreakdown.put("totalCpuCores", totalCpuCores);
        costBreakdown.put("totalMemoryGb", totalMemoryGb + jmMemoryGb);

        Map<String, Object> breakdown = new HashMap<>();
        breakdown.put("taskManagerCpuCostPerHour", tmCpuCostPerHour);
        breakdown.put("taskManagerMemoryCostPerHour", tmMemoryCostPerHour);
        breakdown.put("jobManagerMemoryCostPerHour", jmMemoryCostPerHour);
        breakdown.putAll((Map<String, Object>) networkCost.get("networkCostBreakdown"));
        costBreakdown.put("costBreakdown", breakdown);

        costBreakdown.put("networkCost", networkCost);

        costBreakdown.put("costPerHour", totalCostPerHour);
        costBreakdown.put("costPerDay", totalCostPerHour * 24);
        costBreakdown.put("costPerWeek", totalCostPerHour * 24 * 7);
        costBreakdown.put("costPerMonth", totalCostPerHour * 24 * 30);
        costBreakdown.put("costPerYear", totalCostPerHour * 24 * 365);

        return costBreakdown;
    }

    public Map<String, Object> calculateNetworkCost(ResourceConfig config, NetworkCostModel networkModel) {
        logger.debug("Calculating network cost for {} TaskManagers", config.getNumTaskManagers());

        RackTopology topology = RackTopology.getDefaultTopology(config.getNumTaskManagers());

        double crossRackRatio = topology.calculateCrossRackTrafficRatio(config.getNumTaskManagers());
        double crossAzRatio = topology.calculateCrossAzTrafficRatio(config.getNumTaskManagers());
        double intraRackRatio = 1 - crossRackRatio - crossAzRatio;

        long totalBytesPerHour = calculateTotalNetworkTraffic(config, networkModel);
        double totalGbPerHour = totalBytesPerHour / (1024.0 * 1024 * 1024);

        double crossRackGbPerHour = totalGbPerHour * crossRackRatio;
        double crossAzGbPerHour = totalGbPerHour * crossAzRatio;
        double intraDcGbPerHour = totalGbPerHour * intraRackRatio;

        double crossRackCostPerHour = crossRackGbPerHour * costPerGbCrossRack;
        double crossAzCostPerHour = crossAzGbPerHour * costPerGbCrossAz;
        double intraDcCostPerHour = intraDcGbPerHour * costPerGbNetworkOut * 0.5;
        double egressCostPerHour = totalGbPerHour * costPerGbNetworkOut;

        double totalNetworkCostPerHour = crossRackCostPerHour + crossAzCostPerHour + intraDcCostPerHour + egressCostPerHour * 0.3;

        Map<String, Object> breakdown = new HashMap<>();
        breakdown.put("crossRackTrafficGbPerHour", crossRackGbPerHour);
        breakdown.put("crossAzTrafficGbPerHour", crossAzGbPerHour);
        breakdown.put("intraDcTrafficGbPerHour", intraDcGbPerHour);
        breakdown.put("totalTrafficGbPerHour", totalGbPerHour);
        breakdown.put("crossRackCostPerHour", crossRackCostPerHour);
        breakdown.put("crossAzCostPerHour", crossAzCostPerHour);
        breakdown.put("intraDcCostPerHour", intraDcCostPerHour);
        breakdown.put("egressCostPerHour", egressCostPerHour * 0.3);
        breakdown.put("networkCostPerHour", totalNetworkCostPerHour);

        Map<String, Object> networkCost = new HashMap<>();
        networkCost.put("topology", Map.of(
                "availabilityZones", topology.getAvailabilityZones(),
                "racksPerAz", topology.getRacksPerAz(),
                "taskManagersPerRack", topology.getTaskManagersPerRack(),
                "crossRackRatio", crossRackRatio,
                "crossAzRatio", crossAzRatio,
                "intraRackRatio", intraRackRatio
        ));
        networkCost.put("trafficBreakdown", Map.of(
                "totalBytesPerHour", totalBytesPerHour,
                "totalGbPerHour", totalGbPerHour,
                "crossRackPercentage", crossRackRatio * 100,
                "crossAzPercentage", crossAzRatio * 100,
                "intraRackPercentage", intraRackRatio * 100
        ));
        networkCost.put("networkCostBreakdown", breakdown);
        networkCost.put("totalNetworkCostPerHour", totalNetworkCostPerHour);
        networkCost.put("totalNetworkCostPerDay", totalNetworkCostPerHour * 24);
        networkCost.put("totalNetworkCostPerMonth", totalNetworkCostPerHour * 24 * 30);
        networkCost.put("costModel", networkModel);

        return networkCost;
    }

    private long calculateTotalNetworkTraffic(ResourceConfig config, NetworkCostModel networkModel) {
        long recordsPerSec = networkModel.getRecordsPerSecond();
        double bytesPerRecordIn = networkModel.getAvgBytesPerRecordIn();
        double bytesPerRecordOut = networkModel.getAvgBytesPerRecordOut();

        double shuffleAmplificationFactor = 2.5;
        double totalBytesPerSec = recordsPerSec * (bytesPerRecordIn + bytesPerRecordOut) * shuffleAmplificationFactor;

        return (long) (totalBytesPerSec * 3600);
    }

    public Map<String, Object> compareCosts(ResourceConfig currentConfig, ResourceConfig proposedConfig) {
        return compareCosts(currentConfig, proposedConfig, NetworkCostModel.getDefaultModel());
    }

    public Map<String, Object> compareCosts(
            ResourceConfig currentConfig,
            ResourceConfig proposedConfig,
            NetworkCostModel networkModel) {
        logger.info("Comparing costs between configurations");

        Map<String, Object> currentCost = calculateJobCost(currentConfig, networkModel);
        Map<String, Object> proposedCost = calculateJobCost(proposedConfig, networkModel);

        double currentCostPerHour = (Double) currentCost.get("costPerHour");
        double proposedCostPerHour = (Double) proposedCost.get("costPerHour");

        double costDifference = proposedCostPerHour - currentCostPerHour;
        double costDifferencePercent = currentCostPerHour > 0
                ? (costDifference / currentCostPerHour) * 100
                : 0;

        Map<String, Object> currentNetworkCost = (Map<String, Object>) currentCost.get("networkCost");
        Map<String, Object> proposedNetworkCost = (Map<String, Object>) proposedCost.get("networkCost");

        double currentNetworkPerHour = (Double) currentNetworkCost.get("totalNetworkCostPerHour");
        double proposedNetworkPerHour = (Double) proposedNetworkCost.get("totalNetworkCostPerHour");
        double networkCostDifference = proposedNetworkPerHour - currentNetworkPerHour;

        Map<String, Object> comparison = new HashMap<>();
        comparison.put("currentCost", currentCost);
        comparison.put("proposedCost", proposedCost);
        comparison.put("costDifferencePerHour", costDifference);
        comparison.put("costDifferencePercent", costDifferencePercent);
        comparison.put("costDifferencePerDay", costDifference * 24);
        comparison.put("costDifferencePerMonth", costDifference * 24 * 30);
        comparison.put("costDifferencePerYear", costDifference * 24 * 365);
        comparison.put("isSavings", costDifference < 0);
        comparison.put("savingsPerYear", Math.max(0, -costDifference * 24 * 365));
        comparison.put("networkCostDifference", Map.of(
                "current", currentNetworkPerHour,
                "proposed", proposedNetworkPerHour,
                "difference", networkCostDifference,
                "differencePercent", currentNetworkPerHour > 0
                        ? (networkCostDifference / currentNetworkPerHour) * 100 : 0
        ));

        return comparison;
    }

    public Map<String, Object> calculateTotalCostOfOwnership(ResourceConfig config, int months) {
        return calculateTotalCostOfOwnership(config, months, NetworkCostModel.getDefaultModel());
    }

    public Map<String, Object> calculateTotalCostOfOwnership(
            ResourceConfig config,
            int months,
            NetworkCostModel networkModel) {
        logger.debug("Calculating TCO for {} months", months);

        Map<String, Object> cost = calculateJobCost(config, networkModel);
        double monthlyCost = (Double) cost.get("costPerMonth");

        Map<String, Object> networkCost = (Map<String, Object>) cost.get("networkCost");
        double monthlyNetworkCost = (Double) networkCost.get("totalNetworkCostPerMonth");

        double totalCost = monthlyCost * months;
        double upfrontCost = 0;

        Map<String, Object> tco = new HashMap<>();
        tco.put("upfrontCost", upfrontCost);
        tco.put("recurringMonthlyCost", monthlyCost);
        tco.put("networkMonthlyCost", monthlyNetworkCost);
        tco.put("computeMonthlyCost", monthlyCost - monthlyNetworkCost);
        tco.put("totalRecurringCost", monthlyCost * months);
        tco.put("totalNetworkCost", monthlyNetworkCost * months);
        tco.put("totalComputeCost", (monthlyCost - monthlyNetworkCost) * months);
        tco.put("totalCostOfOwnership", upfrontCost + monthlyCost * months);
        tco.put("calculationPeriodMonths", months);

        Map<String, Object> assumptions = new HashMap<>();
        assumptions.put("costPerCpuPerHour", costPerCpuPerHour);
        assumptions.put("costPerGbMemoryPerHour", costPerGbMemoryPerHour);
        assumptions.put("costPerGbCrossRack", costPerGbCrossRack);
        assumptions.put("costPerGbCrossAz", costPerGbCrossAz);
        assumptions.put("costPerGbNetworkOut", costPerGbNetworkOut);
        assumptions.put("hoursPerDay", 24);
        assumptions.put("daysPerMonth", 30);
        assumptions.put("networkModel", networkModel);
        tco.put("assumptions", assumptions);

        return tco;
    }

    public Map<String, Object> getCostOptimizationTips(ResourceConfig config) {
        return getCostOptimizationTips(config, NetworkCostModel.getDefaultModel());
    }

    public Map<String, Object> getCostOptimizationTips(ResourceConfig config, NetworkCostModel networkModel) {
        logger.debug("Generating cost optimization tips");

        Map<String, Object> tips = new HashMap<>();
        double taskManagerMemoryGb = config.getTaskManagerMemoryMb() / 1024.0;

        if (taskManagerMemoryGb > 8) {
            tips.put("memoryOptimization", Map.of(
                    "tip", "Consider reducing TaskManager memory",
                    "current", taskManagerMemoryGb + " GB",
                    "recommended", "4-8 GB",
                    "potentialSavingsPercent", 15.0
            ));
        }

        if (config.getTaskManagerCpuCores() > 4) {
            tips.put("cpuOptimization", Map.of(
                    "tip", "Consider using smaller TaskManagers with fewer CPU cores",
                    "current", config.getTaskManagerCpuCores() + " cores",
                    "recommended", "1-4 cores",
                    "potentialSavingsPercent", 10.0
            ));
        }

        if (config.getNumTaskManagers() > 10) {
            RackTopology topology = RackTopology.getDefaultTopology(config.getNumTaskManagers());
            double crossRackRatio = topology.calculateCrossRackTrafficRatio(config.getNumTaskManagers());

            tips.put("consolidation", Map.of(
                    "tip", "Consider consolidating to fewer, larger TaskManagers",
                    "current", config.getNumTaskManagers() + " TaskManagers",
                    "recommended", "Fewer, larger instances",
                    "crossRackTrafficRatio", crossRackRatio,
                    "potentialSavingsPercent", 5.0 + crossRackRatio * 10
            ));
        }

        Map<String, Object> networkCost = calculateNetworkCost(config, networkModel);
        @SuppressWarnings("unchecked")
        Map<String, Object> trafficBreakdown = (Map<String, Object>) networkCost.get("trafficBreakdown");
        double crossAzPercent = (Double) trafficBreakdown.get("crossAzPercentage");

        if (crossAzPercent > 15) {
            tips.put("networkOptimization", Map.of(
                    "tip", "Consider reducing cross-AZ traffic by improving locality",
                    "currentCrossAzTraffic", crossAzPercent + "%",
                    "recommended", "< 10%",
                    "potentialSavingsPercent", crossAzPercent * 0.5
            ));
        }

        return tips;
    }

    public Map<String, Object> simulateScalingCosts(ResourceConfig baseConfig, int[] scalingFactors) {
        return simulateScalingCosts(baseConfig, scalingFactors, NetworkCostModel.getDefaultModel());
    }

    public Map<String, Object> simulateScalingCosts(
            ResourceConfig baseConfig,
            int[] scalingFactors,
            NetworkCostModel networkModel) {
        logger.info("Simulating scaling costs for factors: {}", scalingFactors);

        Map<String, Object> simulations = new HashMap<>();

        for (int factor : scalingFactors) {
            ResourceConfig scaledConfig = ResourceConfig.builder()
                    .jobId(baseConfig.getJobId())
                    .jobName(baseConfig.getJobName())
                    .jobManagerMemoryMb(baseConfig.getJobManagerMemoryMb())
                    .taskManagerMemoryMb(baseConfig.getTaskManagerMemoryMb())
                    .taskManagerCpuCores(baseConfig.getTaskManagerCpuCores())
                    .numTaskManagers((int) Math.ceil(baseConfig.getNumTaskManagers() * factor / 100.0))
                    .parallelism((int) Math.ceil(baseConfig.getParallelism() * factor / 100.0))
                    .build();

            NetworkCostModel scaledNetworkModel = NetworkCostModel.builder()
                    .costPerGbInTraffic(networkModel.getCostPerGbInTraffic())
                    .costPerGbOutTraffic(networkModel.getCostPerGbOutTraffic())
                    .costPerGbIntraDcTraffic(networkModel.getCostPerGbIntraDcTraffic())
                    .costPerGbCrossRackTraffic(networkModel.getCostPerGbCrossRackTraffic())
                    .costPerGbCrossAzTraffic(networkModel.getCostPerGbCrossAzTraffic())
                    .avgBytesPerRecordIn(networkModel.getAvgBytesPerRecordIn())
                    .avgBytesPerRecordOut(networkModel.getAvgBytesPerRecordOut())
                    .recordsPerSecond((long) (networkModel.getRecordsPerSecond() * factor / 100.0))
                    .build();

            Map<String, Object> cost = calculateJobCost(scaledConfig, scaledNetworkModel);
            simulations.put(factor + "percent", Map.of(
                    "config", scaledConfig,
                    "cost", cost
            ));
        }

        return simulations;
    }

    public Map<String, Object> getNetworkCostReport(ResourceConfig config) {
        Map<String, Object> report = new HashMap<>();

        NetworkCostModel[] models = {
                NetworkCostModel.getLowTrafficModel(),
                NetworkCostModel.getDefaultModel(),
                NetworkCostModel.getHighTrafficModel()
        };

        Map<String, Map<String, Object>> scenarios = new HashMap<>();

        for (NetworkCostModel model : models) {
            Map<String, Object> networkCost = calculateNetworkCost(config, model);
            String scenarioName = model.getRecordsPerSecond() <= 1000 ? "LOW_TRAFFIC"
                    : model.getRecordsPerSecond() <= 10000 ? "MEDIUM_TRAFFIC" : "HIGH_TRAFFIC";
            scenarios.put(scenarioName, networkCost);
        }

        report.put("config", config);
        report.put("scenarios", scenarios);
        report.put("costRates", Map.of(
                "crossRackPerGb", costPerGbCrossRack,
                "crossAzPerGb", costPerGbCrossAz,
                "egressPerGb", costPerGbNetworkOut
        ));

        return report;
    }
}
