package com.abtest.service;

import com.abtest.dto.StatisticalResultDTO;
import org.apache.commons.math3.distribution.NormalDistribution;
import org.apache.commons.math3.distribution.TDistribution;
import org.apache.commons.math3.stat.inference.ChiSquareTest;
import org.apache.commons.math3.stat.inference.TTest;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class StatisticsService {

    private static final double DEFAULT_CONFIDENCE_LEVEL = 0.95;
    private static final double SIGNIFICANCE_LEVEL = 0.05;

    private final TTest tTest = new TTest();
    private final ChiSquareTest chiSquareTest = new ChiSquareTest();
    private final NormalDistribution normalDistribution = new NormalDistribution(0, 1);

    public StatisticalResultDTO performTTest(String metricName, String controlVariant, String testVariant,
                                              Map<String, Object> controlStats, Map<String, Object> testStats) {
        return performTTest(metricName, controlVariant, testVariant, controlStats, testStats, 1);
    }

    public StatisticalResultDTO performTTest(String metricName, String controlVariant, String testVariant,
                                              Map<String, Object> controlStats, Map<String, Object> testStats,
                                              int comparisonCount) {
        StatisticalResultDTO result = new StatisticalResultDTO();
        result.setMetricName(metricName);
        result.setControlVariant(controlVariant);
        result.setTestVariant(testVariant);
        result.setTestType("T-Test");
        result.setConfidenceLevel(DEFAULT_CONFIDENCE_LEVEL);
        result.setComparisonCount(comparisonCount);

        double controlMean = ((Number) controlStats.getOrDefault("avgValue", 0.0)).doubleValue();
        double testMean = ((Number) testStats.getOrDefault("avgValue", 0.0)).doubleValue();
        double controlStd = ((Number) controlStats.getOrDefault("stddevValue", 0.0)).doubleValue();
        double testStd = ((Number) testStats.getOrDefault("stddevValue", 0.0)).doubleValue();
        int controlN = ((Number) controlStats.getOrDefault("userCount", 0)).intValue();
        int testN = ((Number) testStats.getOrDefault("userCount", 0)).intValue();

        result.setControlValue(controlMean);
        result.setTestValue(testMean);
        result.setAbsoluteChange(testMean - controlMean);
        result.setRelativeChange(controlMean != 0 ? (testMean - controlMean) / controlMean * 100 : 0.0);

        if (controlN < 2 || testN < 2 || (controlStd == 0 && testStd == 0)) {
            setInsufficientDataResult(result);
            return result;
        }

        double pValue = performWelchTTest(controlMean, testMean, controlStd, testStd, controlN, testN);
        result.setPValue(pValue);

        double pooledSE = Math.sqrt((controlStd * controlStd / controlN) + (testStd * testStd / testN));
        double df = calculateWelchDF(controlStd, testStd, controlN, testN);
        TDistribution tDist = new TDistribution(df);
        double criticalValue = tDist.inverseCumulativeProbability(1 - SIGNIFICANCE_LEVEL / 2);
        double marginOfError = criticalValue * pooledSE;

        double meanDiff = testMean - controlMean;
        result.setConfidenceIntervalLower(meanDiff - marginOfError);
        result.setConfidenceIntervalUpper(meanDiff + marginOfError);

        boolean significant = pValue < SIGNIFICANCE_LEVEL;
        result.setIsStatisticallySignificant(significant);
        result.setSignificance(determineSignificance(significant, meanDiff));

        applyBonferroniCorrection(result, pValue, meanDiff, pooledSE, tDist, comparisonCount);

        return result;
    }

    public StatisticalResultDTO performChiSquareTest(String metricName, String controlVariant, String testVariant,
                                                      Map<String, Object> controlStats, Map<String, Object> testStats) {
        return performChiSquareTest(metricName, controlVariant, testVariant, controlStats, testStats, 1);
    }

    public StatisticalResultDTO performChiSquareTest(String metricName, String controlVariant, String testVariant,
                                                      Map<String, Object> controlStats, Map<String, Object> testStats,
                                                      int comparisonCount) {
        StatisticalResultDTO result = new StatisticalResultDTO();
        result.setMetricName(metricName);
        result.setControlVariant(controlVariant);
        result.setTestVariant(testVariant);
        result.setTestType("Chi-Square Test");
        result.setConfidenceLevel(DEFAULT_CONFIDENCE_LEVEL);
        result.setComparisonCount(comparisonCount);

        int controlTotal = ((Number) controlStats.getOrDefault("totalUsers", 0)).intValue();
        int controlConverted = ((Number) controlStats.getOrDefault("convertedUsers", 0)).intValue();
        int testTotal = ((Number) testStats.getOrDefault("totalUsers", 0)).intValue();
        int testConverted = ((Number) testStats.getOrDefault("convertedUsers", 0)).intValue();

        double controlRate = controlTotal > 0 ? (double) controlConverted / controlTotal : 0.0;
        double testRate = testTotal > 0 ? (double) testConverted / testTotal : 0.0;

        result.setControlValue(controlRate);
        result.setTestValue(testRate);
        result.setAbsoluteChange(testRate - controlRate);
        result.setRelativeChange(controlRate != 0 ? (testRate - controlRate) / controlRate * 100 : 0.0);

        if (controlTotal == 0 || testTotal == 0) {
            setInsufficientDataResult(result);
            return result;
        }

        long[][] observed = {
            {controlConverted, controlTotal - controlConverted},
            {testConverted, testTotal - testConverted}
        };

        try {
            double pValue = chiSquareTest.chiSquareTest(observed);
            result.setPValue(pValue);

            double se = Math.sqrt(
                (controlRate * (1 - controlRate) / controlTotal) +
                (testRate * (1 - testRate) / testTotal)
            );
            double zScore = normalDistribution.inverseCumulativeProbability(1 - SIGNIFICANCE_LEVEL / 2);
            double marginOfError = zScore * se;

            double rateDiff = testRate - controlRate;
            result.setConfidenceIntervalLower(rateDiff - marginOfError);
            result.setConfidenceIntervalUpper(rateDiff + marginOfError);

            boolean significant = pValue < SIGNIFICANCE_LEVEL;
            result.setIsStatisticallySignificant(significant);
            result.setSignificance(determineSignificance(significant, rateDiff));

            applyBonferroniCorrectionForProportion(result, pValue, rateDiff, se, comparisonCount);

        } catch (Exception e) {
            result.setPValue(1.0);
            result.setIsStatisticallySignificant(false);
            result.setSignificance("ERROR");
            result.setIsBonferroniSignificant(false);
            result.setBonferroniSignificance("ERROR");
        }

        return result;
    }

    private void applyBonferroniCorrection(StatisticalResultDTO result, double pValue,
                                            double meanDiff, double se,
                                            TDistribution tDist, int comparisonCount) {
        if (comparisonCount <= 1) {
            result.setAdjustedPValue(pValue);
            result.setAdjustedConfidenceLevel(DEFAULT_CONFIDENCE_LEVEL);
            result.setAdjustedConfidenceIntervalLower(result.getConfidenceIntervalLower());
            result.setAdjustedConfidenceIntervalUpper(result.getConfidenceIntervalUpper());
            result.setIsBonferroniSignificant(result.getIsStatisticallySignificant());
            result.setBonferroniSignificance(result.getSignificance());
            result.setBonferroniCorrectedAlpha(SIGNIFICANCE_LEVEL);
            return;
        }

        double bonferroniAlpha = SIGNIFICANCE_LEVEL / comparisonCount;
        result.setBonferroniCorrectedAlpha(bonferroniAlpha);

        double adjustedPValue = Math.min(pValue * comparisonCount, 1.0);
        result.setAdjustedPValue(adjustedPValue);

        double adjustedConfidenceLevel = 1 - bonferroniAlpha;
        result.setAdjustedConfidenceLevel(adjustedConfidenceLevel);

        double adjustedCriticalValue = tDist.inverseCumulativeProbability(1 - bonferroniAlpha / 2);
        double adjustedMarginOfError = adjustedCriticalValue * se;
        result.setAdjustedConfidenceIntervalLower(meanDiff - adjustedMarginOfError);
        result.setAdjustedConfidenceIntervalUpper(meanDiff + adjustedMarginOfError);

        boolean bonferroniSignificant = adjustedPValue < SIGNIFICANCE_LEVEL;
        result.setIsBonferroniSignificant(bonferroniSignificant);
        result.setBonferroniSignificance(determineSignificance(bonferroniSignificant, meanDiff));
    }

    private void applyBonferroniCorrectionForProportion(StatisticalResultDTO result, double pValue,
                                                         double rateDiff, double se,
                                                         int comparisonCount) {
        if (comparisonCount <= 1) {
            result.setAdjustedPValue(pValue);
            result.setAdjustedConfidenceLevel(DEFAULT_CONFIDENCE_LEVEL);
            result.setAdjustedConfidenceIntervalLower(result.getConfidenceIntervalLower());
            result.setAdjustedConfidenceIntervalUpper(result.getConfidenceIntervalUpper());
            result.setIsBonferroniSignificant(result.getIsStatisticallySignificant());
            result.setBonferroniSignificance(result.getSignificance());
            result.setBonferroniCorrectedAlpha(SIGNIFICANCE_LEVEL);
            return;
        }

        double bonferroniAlpha = SIGNIFICANCE_LEVEL / comparisonCount;
        result.setBonferroniCorrectedAlpha(bonferroniAlpha);

        double adjustedPValue = Math.min(pValue * comparisonCount, 1.0);
        result.setAdjustedPValue(adjustedPValue);

        double adjustedConfidenceLevel = 1 - bonferroniAlpha;
        result.setAdjustedConfidenceLevel(adjustedConfidenceLevel);

        double adjustedZScore = normalDistribution.inverseCumulativeProbability(1 - bonferroniAlpha / 2);
        double adjustedMarginOfError = adjustedZScore * se;
        result.setAdjustedConfidenceIntervalLower(rateDiff - adjustedMarginOfError);
        result.setAdjustedConfidenceIntervalUpper(rateDiff + adjustedMarginOfError);

        boolean bonferroniSignificant = adjustedPValue < SIGNIFICANCE_LEVEL;
        result.setIsBonferroniSignificant(bonferroniSignificant);
        result.setBonferroniSignificance(determineSignificance(bonferroniSignificant, rateDiff));
    }

    private String determineSignificance(boolean significant, double diff) {
        if (significant) {
            return diff > 0 ? "POSITIVE" : "NEGATIVE";
        } else {
            return "NOT_SIGNIFICANT";
        }
    }

    private void setInsufficientDataResult(StatisticalResultDTO result) {
        result.setPValue(1.0);
        result.setAdjustedPValue(1.0);
        result.setIsStatisticallySignificant(false);
        result.setIsBonferroniSignificant(false);
        result.setSignificance("INSUFFICIENT_DATA");
        result.setBonferroniSignificance("INSUFFICIENT_DATA");
        result.setBonferroniCorrectedAlpha(result.getComparisonCount() > 1
            ? SIGNIFICANCE_LEVEL / result.getComparisonCount()
            : SIGNIFICANCE_LEVEL);
    }

    private double performWelchTTest(double mean1, double mean2, double std1, double std2, int n1, int n2) {
        double se = Math.sqrt((std1 * std1 / n1) + (std2 * std2 / n2));
        if (se == 0) {
            return 1.0;
        }
        double tStat = Math.abs(mean1 - mean2) / se;
        double df = calculateWelchDF(std1, std2, n1, n2);
        TDistribution tDist = new TDistribution(df);
        return 2 * (1 - tDist.cumulativeProbability(tStat));
    }

    private double calculateWelchDF(double std1, double std2, int n1, int n2) {
        double var1 = std1 * std1;
        double var2 = std2 * std2;
        double numerator = Math.pow(var1 / n1 + var2 / n2, 2);
        double denominator = Math.pow(var1 / n1, 2) / (n1 - 1) + Math.pow(var2 / n2, 2) / (n2 - 1);
        return denominator > 0 ? numerator / denominator : 1.0;
    }

    public double calculateSampleSize(double baselineRate, double minimumDetectableEffect,
                                       double alpha, double power) {
        double p1 = baselineRate;
        double p2 = p1 * (1 + minimumDetectableEffect);

        double zAlpha = normalDistribution.inverseCumulativeProbability(1 - alpha / 2);
        double zBeta = normalDistribution.inverseCumulativeProbability(power);

        double pBar = (p1 + p2) / 2;
        double qBar = 1 - pBar;

        double numerator = (zAlpha * Math.sqrt(2 * pBar * qBar) + zBeta * Math.sqrt(p1 * (1 - p1) + p2 * (1 - p2)));
        double denominator = Math.pow(p2 - p1, 2);

        return Math.ceil(2 * Math.pow(numerator, 2) / denominator);
    }

    public double calculateSampleSizeWithBonferroni(double baselineRate, double minimumDetectableEffect,
                                                     double alpha, double power, int comparisonCount) {
        double correctedAlpha = alpha / comparisonCount;
        return calculateSampleSize(baselineRate, minimumDetectableEffect, correctedAlpha, power);
    }
}
