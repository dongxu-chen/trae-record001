package com.tracing.sampling.predictor;

import com.tracing.sampling.model.TrafficTimeSeriesData;
import com.tracing.sampling.model.TrafficTimeSeriesData.TimeWindowData;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.LinkedList;
import java.util.List;

@Component
public class TrafficPredictor {

    private static final Logger logger = LoggerFactory.getLogger(TrafficPredictor.class);
    
    private static final int HISTORY_WINDOWS = 12;
    private static final double TREND_SENSITIVITY = 0.3;
    private static final double SEASONALITY_WEIGHT = 0.2;
    
    private final TrafficTimeSeriesData trafficData;
    private final List<Double> historicalPredictions;
    
    private double ewmaRequestsPerSecond = 0.0;
    private double trendSlope = 0.0;
    private double forecastError = 0.0;

    public TrafficPredictor() {
        this.trafficData = new TrafficTimeSeriesData(HISTORY_WINDOWS);
        this.historicalPredictions = new LinkedList<>();
    }

    public synchronized void recordTrafficData(long windowDurationSeconds, 
                                                long requestCount, 
                                                long errorCount, 
                                                long totalLatency) {
        long timestamp = System.currentTimeMillis();
        TimeWindowData data = new TimeWindowData(
                timestamp, windowDurationSeconds, requestCount, errorCount, totalLatency);
        trafficData.addDataPoint(data);
        
        double actualRps = data.getRequestsPerSecond();
        updateEWMA(actualRps);
        updateTrend(actualRps);
        
        if (historicalPredictions.size() >= HISTORY_WINDOWS) {
            historicalPredictions.remove(0);
        }
        
        logger.debug("Recorded traffic: window={}s, requests={}, errors={}, avgLatency={}ms, rps={:.2f}",
                windowDurationSeconds, requestCount, errorCount, data.getAverageLatency(), actualRps);
    }

    public synchronized PredictionResult predictTraffic(int lookAheadSeconds) {
        int dataPoints = trafficData.getDataPointCount();
        if (dataPoints == 0) {
            return new PredictionResult(0.0, 0.0, 0.0, PredictionConfidence.LOW);
        }

        double basePrediction = ewmaRequestsPerSecond;
        double trendComponent = trendSlope * lookAheadSeconds;
        double predictedRps = basePrediction + trendComponent;
        
        double seasonalityFactor = calculateSeasonalityFactor();
        predictedRps *= seasonalityFactor;
        
        double errorRate = trafficData.getErrorRate();
        double avgLatency = trafficData.getAverageLatency();
        
        PredictionConfidence confidence = calculateConfidence(dataPoints, forecastError);
        
        double upperBound = predictedRps * (1 + forecastError + 0.1);
        double lowerBound = predictedRps * Math.max(0, 1 - forecastError - 0.1);
        
        logger.debug("Traffic prediction: lookAhead={}s, predictedRps={:.2f}, errorRate={:.2%}, " +
                        "confidence={}, trend={:.4f}, seasonality={:.2f}",
                lookAheadSeconds, predictedRps, errorRate, confidence, trendSlope, seasonalityFactor);
        
        return new PredictionResult(
                Math.max(0, predictedRps),
                Math.max(0, lowerBound),
                upperBound,
                confidence,
                errorRate,
                avgLatency,
                basePrediction,
                trendComponent,
                seasonalityFactor
        );
    }

    private void updateEWMA(double actualRps) {
        double alpha = 0.3;
        if (ewmaRequestsPerSecond == 0.0) {
            ewmaRequestsPerSecond = actualRps;
        } else {
            ewmaRequestsPerSecond = alpha * actualRps + (1 - alpha) * ewmaRequestsPerSecond;
        }
    }

    private void updateTrend(double actualRps) {
        if (historicalPredictions.isEmpty()) {
            return;
        }
        
        double lastPrediction = historicalPredictions.get(historicalPredictions.size() - 1);
        double error = lastPrediction > 0 ? Math.abs(actualRps - lastPrediction) / lastPrediction : 0;
        forecastError = 0.8 * forecastError + 0.2 * error;
        
        if (trafficData.getDataPointCount() >= 2) {
            double prevRps = ewmaRequestsPerSecond;
            double newTrend = (actualRps - prevRps) * TREND_SENSITIVITY;
            trendSlope = 0.7 * trendSlope + 0.3 * newTrend;
        }
    }

    private double calculateSeasonalityFactor() {
        if (trafficData.getDataPointCount() < 4) {
            return 1.0;
        }
        
        long currentTime = System.currentTimeMillis();
        int currentHour = (int) ((currentTime / (1000 * 60 * 60)) % 24);
        int currentMinute = (int) ((currentTime / (1000 * 60)) % 60);
        
        double timeOfDayFactor = 1.0;
        if (currentHour >= 9 && currentHour <= 17) {
            timeOfDayFactor = 1.2;
        } else if (currentHour >= 18 && currentHour <= 22) {
            timeOfDayFactor = 1.1;
        } else if (currentHour >= 0 && currentHour <= 6) {
            timeOfDayFactor = 0.6;
        }
        
        return 1.0 + (timeOfDayFactor - 1.0) * SEASONALITY_WEIGHT;
    }

    private PredictionConfidence calculateConfidence(int dataPoints, double error) {
        if (dataPoints < 3) {
            return PredictionConfidence.LOW;
        } else if (dataPoints < 6 || error > 0.3) {
            return PredictionConfidence.MEDIUM;
        } else if (error > 0.15) {
            return PredictionConfidence.HIGH;
        } else {
            return PredictionConfidence.VERY_HIGH;
        }
    }

    public synchronized double getCurrentErrorRate() {
        return trafficData.getErrorRate();
    }

    public synchronized double getCurrentRps() {
        return trafficData.getAverageRequestsPerSecond();
    }

    public synchronized long getCurrentAvgLatency() {
        return trafficData.getAverageLatency();
    }

    public synchronized int getDataPointCount() {
        return trafficData.getDataPointCount();
    }

    public enum PredictionConfidence {
        LOW(0.5),
        MEDIUM(0.75),
        HIGH(0.9),
        VERY_HIGH(0.98);

        private final double factor;

        PredictionConfidence(double factor) {
            this.factor = factor;
        }

        public double getFactor() {
            return factor;
        }
    }

    public static class PredictionResult {
        private final double predictedRps;
        private final double lowerBound;
        private final double upperBound;
        private final PredictionConfidence confidence;
        private final double errorRate;
        private final double averageLatency;
        private final double basePrediction;
        private final double trendComponent;
        private final double seasonalityFactor;

        public PredictionResult(double predictedRps, double lowerBound, double upperBound,
                                PredictionConfidence confidence) {
            this(predictedRps, lowerBound, upperBound, confidence, 0.0, 0, 0.0, 0.0, 1.0);
        }

        public PredictionResult(double predictedRps, double lowerBound, double upperBound,
                                PredictionConfidence confidence, double errorRate, double averageLatency,
                                double basePrediction, double trendComponent, double seasonalityFactor) {
            this.predictedRps = predictedRps;
            this.lowerBound = lowerBound;
            this.upperBound = upperBound;
            this.confidence = confidence;
            this.errorRate = errorRate;
            this.averageLatency = averageLatency;
            this.basePrediction = basePrediction;
            this.trendComponent = trendComponent;
            this.seasonalityFactor = seasonalityFactor;
        }

        public double getPredictedRps() {
            return predictedRps;
        }

        public double getLowerBound() {
            return lowerBound;
        }

        public double getUpperBound() {
            return upperBound;
        }

        public PredictionConfidence getConfidence() {
            return confidence;
        }

        public double getErrorRate() {
            return errorRate;
        }

        public double getAverageLatency() {
            return averageLatency;
        }

        public double getBasePrediction() {
            return basePrediction;
        }

        public double getTrendComponent() {
            return trendComponent;
        }

        public double getSeasonalityFactor() {
            return seasonalityFactor;
        }
    }
}
