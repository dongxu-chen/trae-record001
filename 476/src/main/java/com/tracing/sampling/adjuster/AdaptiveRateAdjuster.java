package com.tracing.sampling.adjuster;

import com.tracing.sampling.config.TracingProperties;
import com.tracing.sampling.model.SamplingStats;
import com.tracing.sampling.predictor.TrafficPredictor;
import com.tracing.sampling.predictor.TrafficPredictor.PredictionResult;
import com.tracing.sampling.sampler.IntelligentAdaptiveSampler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class AdaptiveRateAdjuster {

    private static final Logger logger = LoggerFactory.getLogger(AdaptiveRateAdjuster.class);

    private static final double ERROR_RATE_THRESHOLD = 0.05;
    private static final double HIGH_ERROR_RATE_MULTIPLIER = 2.0;
    private static final int LOOK_AHEAD_SECONDS = 60;

    private final TracingProperties tracingProperties;
    private final IntelligentAdaptiveSampler sampler;
    private final TrafficPredictor trafficPredictor;

    private double movingAverageSpansPerSecond = 0.0;
    private static final double MOVING_AVERAGE_ALPHA = 0.3;

    private PredictionResult lastPrediction;
    private double errorRateMultiplier = 1.0;

    public AdaptiveRateAdjuster(TracingProperties tracingProperties, 
                               IntelligentAdaptiveSampler sampler,
                               TrafficPredictor trafficPredictor) {
        this.tracingProperties = tracingProperties;
        this.sampler = sampler;
        this.trafficPredictor = trafficPredictor;
    }

    @Scheduled(fixedRateString = "${tracing.sampling.adaptive.adjustment-interval-ms:30000}")
    public void adjustSampleRate() {
        if (!tracingProperties.getSampling().getAdaptive().isEnabled()) {
            return;
        }

        TracingProperties.AdaptiveProperties adaptiveConfig = tracingProperties.getSampling().getAdaptive();
        SamplingStats stats = sampler.getStats();

        long timeWindow = System.currentTimeMillis() - stats.getLastResetTime();
        if (timeWindow < 1000) {
            return;
        }

        recordTrafficData(stats, timeWindow);

        PredictionResult prediction = trafficPredictor.predictTraffic(LOOK_AHEAD_SECONDS);
        this.lastPrediction = prediction;

        double currentSpansPerSecond = (double) stats.getSampledRequests() / (timeWindow / 1000.0);
        movingAverageSpansPerSecond = MOVING_AVERAGE_ALPHA * currentSpansPerSecond +
                (1 - MOVING_AVERAGE_ALPHA) * movingAverageSpansPerSecond;

        double errorRate = prediction.getErrorRate();
        errorRateMultiplier = calculateErrorRateMultiplier(errorRate);

        double targetSpansPerSecond = adaptiveConfig.getTargetSpansPerSecond();
        double predictedRps = prediction.getPredictedRps();
        double currentRate = sampler.getCurrentSampleRate();

        double requiredRate = calculatePredictedRequiredRate(predictedRps, targetSpansPerSecond);
        
        double trendAdjustedRate = applyTrendAdjustment(currentRate, prediction);
        double errorAdjustedRate = trendAdjustedRate * errorRateMultiplier;
        double confidenceAdjustedRate = applyConfidenceAdjustment(errorAdjustedRate, prediction);

        double newRate = confidenceAdjustedRate;
        newRate = Math.max(adaptiveConfig.getMinSampleRate(),
                Math.min(adaptiveConfig.getMaxSampleRate(), newRate));

        if (Math.abs(newRate - currentRate) > 0.001) {
            logger.info("Predictive rate adjustment: " +
                            "currentRate={:.4f}, newRate={:.4f}, " +
                            "predictedRps={:.2f}, currentSPS={:.2f}, targetSPS={}, " +
                            "errorRate={:.2%}, errorMultiplier={:.2f}, " +
                            "confidence={}, trend={:.4f}",
                    currentRate, newRate,
                    predictedRps, movingAverageSpansPerSecond, targetSpansPerSecond,
                    errorRate, errorRateMultiplier,
                    prediction.getConfidence(), prediction.getTrendComponent());
            
            sampler.updateSampleRate(newRate);
        } else {
            logger.debug("Rate adjustment skipped: change too small. " +
                            "currentRate={:.4f}, proposedRate={:.4f}, " +
                            "predictedRps={:.2f}, errorRate={:.2%}",
                    currentRate, newRate, predictedRps, errorRate);
        }

        sampler.resetStats();
    }

    private void recordTrafficData(SamplingStats stats, long timeWindow) {
        long windowSeconds = timeWindow / 1000;
        long requestCount = stats.getTotalRequests();
        long errorCount = stats.getErrorSampled();
        long totalLatency = stats.getTotalRequests() * 100;
        
        trafficPredictor.recordTrafficData(
                windowSeconds,
                requestCount,
                errorCount,
                totalLatency
        );
    }

    private double calculatePredictedRequiredRate(double predictedRps, double targetSps) {
        if (predictedRps <= 0) {
            return sampler.getCurrentSampleRate();
        }
        return targetSps / predictedRps;
    }

    private double calculateErrorRateMultiplier(double errorRate) {
        if (errorRate >= ERROR_RATE_THRESHOLD) {
            double excessError = errorRate - ERROR_RATE_THRESHOLD;
            double multiplier = 1.0 + (excessError * HIGH_ERROR_RATE_MULTIPLIER * 20);
            return Math.min(multiplier, HIGH_ERROR_RATE_MULTIPLIER);
        }
        return 1.0;
    }

    private double applyTrendAdjustment(double currentRate, PredictionResult prediction) {
        double trendComponent = prediction.getTrendComponent();
        double trendFactor = 1.0;
        
        if (trendComponent > 0.1) {
            trendFactor = 1.0 + (trendComponent * 0.5);
        } else if (trendComponent < -0.1) {
            trendFactor = 1.0 + (trendComponent * 0.3);
        }
        
        return currentRate * trendFactor;
    }

    private double applyConfidenceAdjustment(double rate, PredictionResult prediction) {
        double confidenceFactor = prediction.getConfidence().getFactor();
        
        if (confidenceFactor < 0.75) {
            return rate * 0.8;
        } else if (confidenceFactor < 0.9) {
            return rate * 0.9;
        }
        return rate;
    }

    public double getMovingAverageSpansPerSecond() {
        return movingAverageSpansPerSecond;
    }

    public double getErrorRateMultiplier() {
        return errorRateMultiplier;
    }

    public PredictionResult getLastPrediction() {
        return lastPrediction;
    }

    public void triggerAdjustment() {
        adjustSampleRate();
    }
}
