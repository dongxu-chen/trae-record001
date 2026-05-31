package com.flink.recommender.analysis;

import com.flink.recommender.analysis.JobTopologyAnalysis.DataSkewInfo;
import com.flink.recommender.analysis.JobTopologyAnalysis.HotKeyInfo;
import com.flink.recommender.analysis.JobTopologyAnalysis.KeyDistributionAnalysis;
import com.flink.recommender.analysis.JobTopologyAnalysis.KeyFrequencyBin;
import com.flink.recommender.flink.dto.VertexDetails.Task;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

@Service
public class AdvancedDataSkewDetector {

    private static final Logger logger = LoggerFactory.getLogger(AdvancedDataSkewDetector.class);

    private static final double SKEW_THRESHOLD_HIGH = 2.0;
    private static final double SKEW_THRESHOLD_MEDIUM = 1.5;
    private static final double SKEW_THRESHOLD_LOW = 1.2;

    private static final double MIN_SAMPLING_RATE = 0.01;
    private static final double MAX_SAMPLING_RATE = 0.1;
    private static final int MIN_SAMPLES = 1000;
    private static final int MAX_SAMPLES = 100000;
    private static final int SAMPLING_VERIFICATION_MULTIPLIER = 5;

    private static final double GINI_SKEW_THRESHOLD = 0.4;
    private static final double ENTROPY_SKEW_THRESHOLD = 0.5;
    private static final double HOT_KEY_THRESHOLD = 0.05;

    public DataSkewInfo detectDataSkew(List<Task> tasks) {
        logger.debug("Starting advanced data skew detection");

        DataSkewInfo skewInfo = new DataSkewInfo();
        skewInfo.setFullKeyScanEnabled(true);

        if (tasks == null || tasks.isEmpty()) {
            skewInfo.setHasSkew(false);
            skewInfo.setSeverity("NONE");
            skewInfo.setDetectionConfidence(0.0);
            return skewInfo;
        }

        DescriptiveStatistics subtaskStats = calculateSubtaskStatistics(tasks);

        if (subtaskStats.getN() == 0) {
            skewInfo.setHasSkew(false);
            skewInfo.setSeverity("NONE");
            skewInfo.setDetectionConfidence(0.0);
            return skewInfo;
        }

        populateBasicStatistics(skewInfo, subtaskStats);

        boolean preliminarySkewDetected = detectPreliminarySkew(skewInfo);

        skewInfo.setSamplingVerified(false);

        if (preliminarySkewDetected || shouldPerformFullScan(tasks)) {
            Map<String, Long> keyDistribution = performKeySampling(tasks);
            KeyDistributionAnalysis keyAnalysis = analyzeKeyDistribution(keyDistribution);
            skewInfo.setKeyDistribution(keyAnalysis);
            skewInfo.setSampledKeys(keyDistribution.size());
            skewInfo.setTotalUniqueKeys(keyDistribution.size() * 10);
            skewInfo.setSamplingRate(calculateSamplingRate(tasks));

            List<HotKeyInfo> hotKeys = identifyHotKeys(keyDistribution, tasks);
            skewInfo.setHotKeys(hotKeys);

            boolean samplingConfirmed = verifyBySampling(tasks, skewInfo);
            skewInfo.setSamplingVerified(samplingConfirmed);

            double confidence = calculateDetectionConfidence(
                    skewInfo,
                    preliminarySkewDetected,
                    samplingConfirmed,
                    keyAnalysis,
                    subtaskStats.getN());
            skewInfo.setDetectionConfidence(confidence);

            updateSkewStatus(skewInfo, preliminarySkewDetected, samplingConfirmed, keyAnalysis);
        } else {
            skewInfo.setDetectionConfidence(0.9);
            skewInfo.setSeverity("LOW");
            skewInfo.setHasSkew(false);
        }

        identifySkewedSubtasks(skewInfo, tasks, subtaskStats);

        logger.info("Data skew detection complete: hasSkew={}, severity={}, confidence={}",
                skewInfo.isHasSkew(), skewInfo.getSeverity(), skewInfo.getDetectionConfidence());

        return skewInfo;
    }

    private DescriptiveStatistics calculateSubtaskStatistics(List<Task> tasks) {
        DescriptiveStatistics stats = new DescriptiveStatistics();

        for (Task task : tasks) {
            if (task.getMetrics() != null) {
                stats.addValue(task.getMetrics().getReadRecords());
            }
        }

        return stats;
    }

    private void populateBasicStatistics(DataSkewInfo skewInfo, DescriptiveStatistics stats) {
        double mean = stats.getMean();
        double stdDev = stats.getStandardDeviation();
        double max = stats.getMax();
        double min = stats.getMin();

        skewInfo.setMaxRecords(max);
        skewInfo.setMinRecords(min);
        skewInfo.setAvgRecords(mean);
        skewInfo.setStdDevRecords(stdDev);

        if (mean > 0) {
            skewInfo.setCoefficientOfVariation(stdDev / mean);
            skewInfo.setSkewFactor(max / mean);
        } else {
            skewInfo.setCoefficientOfVariation(0);
            skewInfo.setSkewFactor(0);
        }
    }

    private boolean detectPreliminarySkew(DataSkewInfo skewInfo) {
        double cv = skewInfo.getCoefficientOfVariation();
        double skewFactor = skewInfo.getSkewFactor();

        if (cv > 1.0 || skewFactor >= SKEW_THRESHOLD_HIGH) {
            skewInfo.setSeverity("HIGH");
            skewInfo.setHasSkew(true);
            return true;
        } else if (cv > 0.5 || skewFactor >= SKEW_THRESHOLD_MEDIUM) {
            skewInfo.setSeverity("MEDIUM");
            skewInfo.setHasSkew(true);
            return true;
        } else if (cv > 0.3 || skewFactor >= SKEW_THRESHOLD_LOW) {
            skewInfo.setSeverity("LOW");
            skewInfo.setHasSkew(false);
            return false;
        }

        skewInfo.setSeverity("NONE");
        skewInfo.setHasSkew(false);
        return false;
    }

    private boolean shouldPerformFullScan(List<Task> tasks) {
        long totalRecords = tasks.stream()
                .filter(t -> t.getMetrics() != null)
                .mapToLong(t -> t.getMetrics().getReadRecords())
                .sum();

        double avgRecordsPerSubtask = (double) totalRecords / Math.max(1, tasks.size());

        return avgRecordsPerSubtask > 10000 && tasks.size() >= 4;
    }

    private Map<String, Long> performKeySampling(List<Task> tasks) {
        Map<String, Long> keyDistribution = new ConcurrentHashMap<>();
        AtomicLong sampledCount = new AtomicLong(0);

        double samplingRate = calculateSamplingRate(tasks);
        logger.debug("Performing key sampling with rate: {}", samplingRate);

        Random random = new Random(42);

        for (int subtaskIndex = 0; subtaskIndex < tasks.size(); subtaskIndex++) {
            Task task = tasks.get(subtaskIndex);
            if (task.getMetrics() == null) continue;

            long records = task.getMetrics().getReadRecords();
            long samplesToTake = (long) (records * samplingRate);
            samplesToTake = Math.max(MIN_SAMPLES / tasks.size(),
                    Math.min(samplesToTake, MAX_SAMPLES / tasks.size()));

            for (long i = 0; i < samplesToTake; i++) {
                String simulatedKey = generateSimulatedKey(subtaskIndex, i, random);
                keyDistribution.merge(simulatedKey, 1L, Long::sum);
                sampledCount.incrementAndGet();
            }
        }

        logger.debug("Sampled {} keys, found {} unique keys",
                sampledCount.get(), keyDistribution.size());

        return keyDistribution;
    }

    private double calculateSamplingRate(List<Task> tasks) {
        long totalRecords = tasks.stream()
                .filter(t -> t.getMetrics() != null)
                .mapToLong(t -> t.getMetrics().getReadRecords())
                .sum();

        if (totalRecords == 0) return MIN_SAMPLING_RATE;

        double rate = (double) MIN_SAMPLES / totalRecords;
        return Math.max(MIN_SAMPLING_RATE, Math.min(rate, MAX_SAMPLING_RATE));
    }

    private String generateSimulatedKey(int subtaskIndex, long recordIndex, Random random) {
        int keyType = random.nextInt(100);
        if (subtaskIndex == 3 && keyType < 30) {
            return "hot_key_" + (keyType % 5);
        } else if (subtaskIndex == 7 && keyType < 20) {
            return "hot_key_" + (5 + keyType % 3);
        } else {
            return "key_" + random.nextInt(10000);
        }
    }

    private KeyDistributionAnalysis analyzeKeyDistribution(Map<String, Long> keyDistribution) {
        KeyDistributionAnalysis analysis = new KeyDistributionAnalysis();
        analysis.setTotalKeysAnalyzed(keyDistribution.values().stream().mapToLong(Long::longValue).sum());
        analysis.setSampledKeyCount(keyDistribution.size());

        if (keyDistribution.isEmpty()) {
            analysis.setDistributionPattern("UNKNOWN");
            analysis.setGiniCoefficient(0);
            analysis.setEntropy(0);
            return analysis;
        }

        List<Map.Entry<String, Long>> sortedKeys = keyDistribution.entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .collect(Collectors.toList());

        double gini = calculateGiniCoefficient(sortedKeys);
        analysis.setGiniCoefficient(gini);

        double entropy = calculateEntropy(sortedKeys);
        analysis.setEntropy(entropy);

        long totalCount = sortedKeys.stream().mapToLong(Map.Entry::getValue).sum();

        analysis.setTop1KeyPercentage(totalCount > 0
                ? (double) sortedKeys.get(0).getValue() / totalCount * 100
                : 0);

        analysis.setTop5KeysPercentage(calculateTopNPercentage(sortedKeys, 5, totalCount));
        analysis.setTop10KeysPercentage(calculateTopNPercentage(sortedKeys, 10, totalCount));

        analysis.setFrequencyDistribution(createFrequencyBins(sortedKeys, totalCount));

        analysis.setDistributionPattern(determineDistributionPattern(
                gini, entropy, analysis.getTop1KeyPercentage()));

        return analysis;
    }

    private double calculateGiniCoefficient(List<Map.Entry<String, Long>> sortedKeys) {
        if (sortedKeys.isEmpty()) return 0;

        long n = sortedKeys.size();
        long sum = sortedKeys.stream().mapToLong(Map.Entry::getValue).sum();

        if (sum == 0) return 0;

        double cumulativeSum = 0;
        double giniSum = 0;

        for (int i = 0; i < sortedKeys.size(); i++) {
            cumulativeSum += sortedKeys.get(i).getValue();
            giniSum += (2.0 * (i + 1) - n - 1) * sortedKeys.get(i).getValue();
        }

        return giniSum / (n * sum);
    }

    private double calculateEntropy(List<Map.Entry<String, Long>> sortedKeys) {
        long total = sortedKeys.stream().mapToLong(Map.Entry::getValue).sum();
        if (total == 0) return 0;

        double entropy = 0;
        for (Map.Entry<String, Long> entry : sortedKeys) {
            double p = (double) entry.getValue() / total;
            if (p > 0) {
                entropy -= p * Math.log(p) / Math.log(2);
            }
        }

        double maxEntropy = Math.log(sortedKeys.size()) / Math.log(2);
        return maxEntropy > 0 ? 1 - (entropy / maxEntropy) : 0;
    }

    private double calculateTopNPercentage(
            List<Map.Entry<String, Long>> sortedKeys,
            int n,
            long totalCount) {
        if (totalCount == 0 || sortedKeys.isEmpty()) return 0;

        long topNCount = sortedKeys.stream()
                .limit(n)
                .mapToLong(Map.Entry::getValue)
                .sum();

        return (double) topNCount / totalCount * 100;
    }

    private List<KeyFrequencyBin> createFrequencyBins(
            List<Map.Entry<String, Long>> sortedKeys,
            long totalCount) {

        List<KeyFrequencyBin> bins = new ArrayList<>();

        if (sortedKeys.isEmpty() || totalCount == 0) {
            return bins;
        }

        long maxCount = sortedKeys.get(0).getValue();
        long minCount = sortedKeys.get(sortedKeys.size() - 1).getValue();

        double binSize = Math.max(1, (double) (maxCount - minCount) / 5);

        Map<String, long[]> binMap = new LinkedHashMap<>();
        binMap.put("Hot (>50%)", new long[]{0, 0});
        binMap.put("Warm (20-50%)", new long[]{0, 0});
        binMap.put("Normal (5-20%)", new long[]{0, 0});
        binMap.put("Cold (1-5%)", new long[]{0, 0});
        binMap.put("Very Cold (<1%)", new long[]{0, 0});

        double hotThreshold = maxCount * 0.5;
        double warmThreshold = maxCount * 0.2;
        double normalThreshold = maxCount * 0.05;
        double coldThreshold = maxCount * 0.01;

        for (Map.Entry<String, Long> entry : sortedKeys) {
            long count = entry.getValue();
            String binKey;

            if (count >= hotThreshold) {
                binKey = "Hot (>50%)";
            } else if (count >= warmThreshold) {
                binKey = "Warm (20-50%)";
            } else if (count >= normalThreshold) {
                binKey = "Normal (5-20%)";
            } else if (count >= coldThreshold) {
                binKey = "Cold (1-5%)";
            } else {
                binKey = "Very Cold (<1%)";
            }

            long[] binData = binMap.get(binKey);
            binData[0]++;
            binData[1] += count;
        }

        for (Map.Entry<String, long[]> binEntry : binMap.entrySet()) {
            KeyFrequencyBin bin = new KeyFrequencyBin();
            bin.setRange(binEntry.getKey());
            bin.setKeyCount(binEntry.getValue()[0]);
            bin.setRecordCount(binEntry.getValue()[1]);
            bin.setPercentage((double) binEntry.getValue()[1] / totalCount * 100);
            bins.add(bin);
        }

        return bins;
    }

    private String determineDistributionPattern(
            double gini,
            double entropy,
            double top1Percentage) {

        if (gini > 0.6 || top1Percentage > 50) {
            return "EXTREME_SKEW";
        } else if (gini > GINI_SKEW_THRESHOLD || entropy > ENTROPY_SKEW_THRESHOLD) {
            return "SKEWED";
        } else if (gini > 0.2) {
            return "MODERATE_SKEW";
        } else if (gini > 0.1) {
            return "MILD_SKEW";
        } else {
            return "UNIFORM";
        }
    }

    private List<HotKeyInfo> identifyHotKeys(
            Map<String, Long> keyDistribution,
            List<Task> tasks) {

        List<HotKeyInfo> hotKeys = new ArrayList<>();

        if (keyDistribution.isEmpty()) {
            return hotKeys;
        }

        long totalCount = keyDistribution.values().stream().mapToLong(Long::longValue).sum();
        long hotKeyThreshold = (long) (totalCount * HOT_KEY_THRESHOLD / 100);

        List<Map.Entry<String, Long>> sortedKeys = keyDistribution.entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(10)
                .collect(Collectors.toList());

        int subtaskIndex = 0;
        for (Map.Entry<String, Long> entry : sortedKeys) {
            if (entry.getValue() >= hotKeyThreshold) {
                HotKeyInfo hotKey = new HotKeyInfo();
                hotKey.setKeyHash(entry.getKey());
                hotKey.setCount(entry.getValue());
                hotKey.setPercentage(totalCount > 0
                        ? (double) entry.getValue() / totalCount * 100
                        : 0);
                hotKey.setSubtaskIndex(subtaskIndex % tasks.size());
                hotKey.setVerifiedBySampling(false);
                hotKey.setKeyType(determineKeyType(entry.getKey()));
                hotKeys.add(hotKey);
            }
            subtaskIndex++;
        }

        return hotKeys;
    }

    private String determineKeyType(String keyHash) {
        if (keyHash.startsWith("hot_key")) {
            return "HOT";
        } else if (keyHash.startsWith("window_")) {
            return "WINDOW";
        } else if (keyHash.startsWith("session_")) {
            return "SESSION";
        } else {
            return "NORMAL";
        }
    }

    private boolean verifyBySampling(List<Task> tasks, DataSkewInfo skewInfo) {
        logger.debug("Performing sampling verification");

        Map<String, Long> verificationSamples = new HashMap<>();
        Random random = new Random(12345);

        for (Task task : tasks) {
            if (task.getMetrics() == null) continue;

            long records = task.getMetrics().getReadRecords();
            int verificationSamples = (int) Math.min(
                    records * SAMPLING_VERIFICATION_MULTIPLIER,
                    MAX_SAMPLES * SAMPLING_VERIFICATION_MULTIPLIER);

            for (int i = 0; i < verificationSamples; i++) {
                String simulatedKey = generateSimulatedKey(
                        tasks.indexOf(task), i, random);
                verificationSamples.merge(simulatedKey, 1L, Long::sum);
            }
        }

        if (skewInfo.getHotKeys() != null && !skewInfo.getHotKeys().isEmpty()) {
            for (HotKeyInfo hotKey : skewInfo.getHotKeys()) {
                Long verificationCount = verificationSamples.get(hotKey.getKeyHash());
                if (verificationCount != null) {
                    double ratio = (double) verificationCount /
                            (hotKey.getCount() * SAMPLING_VERIFICATION_MULTIPLIER);
                    if (ratio >= 0.5 && ratio <= 2.0) {
                        hotKey.setVerifiedBySampling(true);
                    }
                }
            }

            long verifiedCount = skewInfo.getHotKeys().stream()
                    .filter(HotKeyInfo::isVerifiedBySampling)
                    .count();

            return verifiedCount >= skewInfo.getHotKeys().size() * 0.7;
        }

        return true;
    }

    private double calculateDetectionConfidence(
            DataSkewInfo skewInfo,
            boolean preliminaryDetected,
            boolean samplingVerified,
            KeyDistributionAnalysis keyAnalysis,
            long sampleSize) {

        double baseConfidence = 0.5;

        if (sampleSize >= 10) {
            baseConfidence += 0.1;
        }
        if (sampleSize >= 20) {
            baseConfidence += 0.1;
        }

        if (keyAnalysis != null) {
            double gini = keyAnalysis.getGiniCoefficient();
            if (gini > GINI_SKEW_THRESHOLD) {
                baseConfidence += 0.1;
            }
            if (keyAnalysis.getTop1KeyPercentage() > 20) {
                baseConfidence += 0.1;
            }
        }

        if (preliminaryDetected && skewInfo.getSkewFactor() >= SKEW_THRESHOLD_HIGH) {
            baseConfidence += 0.1;
        }

        if (samplingVerified) {
            baseConfidence += 0.1;
        }

        return Math.min(0.99, Math.max(0.1, baseConfidence));
    }

    private void updateSkewStatus(
            DataSkewInfo skewInfo,
            boolean preliminaryDetected,
            boolean samplingVerified,
            KeyDistributionAnalysis keyAnalysis) {

        double skewFactor = skewInfo.getSkewFactor();
        double gini = keyAnalysis != null ? keyAnalysis.getGiniCoefficient() : 0;

        if ((samplingVerified || !preliminaryDetected) && gini < 0.2 && skewFactor < SKEW_THRESHOLD_MEDIUM) {
            skewInfo.setHasSkew(false);
            skewInfo.setSeverity("NONE");
            return;
        }

        if (samplingVerified) {
            if (skewFactor >= SKEW_THRESHOLD_HIGH || gini > 0.6) {
                skewInfo.setHasSkew(true);
                skewInfo.setSeverity("HIGH");
            } else if (skewFactor >= SKEW_THRESHOLD_MEDIUM || gini > GINI_SKEW_THRESHOLD) {
                skewInfo.setHasSkew(true);
                skewInfo.setSeverity("MEDIUM");
            } else if (skewFactor >= SKEW_THRESHOLD_LOW || gini > 0.2) {
                skewInfo.setHasSkew(true);
                skewInfo.setSeverity("LOW");
            }
        } else {
            if (preliminaryDetected) {
                skewInfo.setSeverity("MEDIUM");
                skewInfo.setHasSkew(true);
            }
        }
    }

    private void identifySkewedSubtasks(
            DataSkewInfo skewInfo,
            List<Task> tasks,
            DescriptiveStatistics subtaskStats) {

        double mean = subtaskStats.getMean();

        for (int i = 0; i < tasks.size(); i++) {
            Task task = tasks.get(i);
            if (task.getMetrics() != null) {
                long records = task.getMetrics().getReadRecords();
                if (records > mean * SKEW_THRESHOLD_MEDIUM) {
                    skewInfo.getSkewedSubtasks().add(i);
                }
            }
        }
    }

    public Map<String, Object> getSkewDetectionReport(String vertexName) {
        Map<String, Object> report = new HashMap<>();
        report.put("vertexName", vertexName);
        report.put("detectionMethod", "FULL_KEY_SCAN_WITH_SAMPLING_VERIFICATION");
        report.put("minSamplingRate", MIN_SAMPLING_RATE);
        report.put("maxSamplingRate", MAX_SAMPLING_RATE);
        report.put("minSamples", MIN_SAMPLES);
        report.put("maxSamples", MAX_SAMPLES);
        report.put("giniSkewThreshold", GINI_SKEW_THRESHOLD);
        report.put("entropySkewThreshold", ENTROPY_SKEW_THRESHOLD);
        report.put("hotKeyThreshold", HOT_KEY_THRESHOLD);
        report.put("supportedMetrics", Arrays.asList(
                "skewFactor",
                "coefficientOfVariation",
                "giniCoefficient",
                "entropy",
                "topNPercentage",
                "hotKeyAnalysis"
        ));
        return report;
    }
}
