package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.TimeSeriesPoint;
import com.ratelimit.recommender.model.TrafficPrediction;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class TimeSeriesPredictionService {

    public TrafficPrediction predictTraffic(String serviceId, int horizonMinutes) {
        List<TimeSeriesPoint> historicalData = generateHistoricalData(serviceId);

        List<TimeSeriesPoint> predictedData = predictWithArima(historicalData, horizonMinutes);

        double confidence = calculateConfidence(historicalData);

        return TrafficPrediction.builder()
                .historicalData(historicalData)
                .predictedData(predictedData)
                .predictionConfidence(confidence)
                .predictionTime(LocalDateTime.now())
                .predictionHorizonMinutes(horizonMinutes)
                .build();
    }

    private List<TimeSeriesPoint> generateHistoricalData(String serviceId) {
        List<TimeSeriesPoint> data = new ArrayList<>();
        LocalDateTime startTime = LocalDateTime.now().minusHours(24);

        double baseQps = getBaseQpsForService(serviceId);

        for (int i = 0; i < 144; i++) {
            LocalDateTime timestamp = startTime.plusMinutes(i * 10);

            double hourOfDay = timestamp.getHour() + timestamp.getMinute() / 60.0;
            double dailyPattern = calculateDailyPattern(hourOfDay);

            double noise = (Math.random() - 0.5) * 0.2;
            double value = baseQps * dailyPattern * (1 + noise);

            data.add(TimeSeriesPoint.builder()
                    .timestamp(timestamp)
                    .value(Math.max(0, value))
                    .upperBound(value * 1.15)
                    .lowerBound(value * 0.85)
                    .build());
        }

        return data;
    }

    private double getBaseQpsForService(String serviceId) {
        switch (serviceId) {
            case "gateway":
                return 500;
            case "user-service":
                return 200;
            case "order-service":
                return 150;
            case "product-service":
                return 180;
            case "payment-service":
                return 80;
            default:
                return 100;
        }
    }

    private double calculateDailyPattern(double hour) {
        double morningPeak = 8 + Math.random() * 2;
        double eveningPeak = 18 + Math.random() * 2;

        double morningComponent = Math.exp(-0.5 * Math.pow((hour - morningPeak) / 2, 2));
        double eveningComponent = Math.exp(-0.5 * Math.pow((hour - eveningPeak) / 3, 2));
        double baseline = 0.3;

        return baseline + 0.4 * morningComponent + 0.5 * eveningComponent;
    }

    private List<TimeSeriesPoint> predictWithArima(List<TimeSeriesPoint> historicalData, int horizonMinutes) {
        List<TimeSeriesPoint> predictions = new ArrayList<>();

        int dataSize = historicalData.size();
        if (dataSize == 0) {
            return predictions;
        }

        double[] values = historicalData.stream()
                .mapToDouble(TimeSeriesPoint::getValue)
                .toArray();

        double[] trend = estimateTrend(values);
        double[] seasonal = estimateSeasonal(values);

        LocalDateTime startTime = historicalData.get(dataSize - 1).getTimestamp();
        int steps = (horizonMinutes + 9) / 10;

        for (int i = 0; i < steps; i++) {
            LocalDateTime timestamp = startTime.plusMinutes((i + 1) * 10);

            int trendIdx = Math.min(dataSize - 1, i);
            int seasonalIdx = (dataSize + i) % seasonal.length;

            double trendValue = trend[Math.max(0, dataSize - 5 + trendIdx % 5)];
            double seasonalValue = seasonal[seasonalIdx];

            double noise = (Math.random() - 0.5) * 0.15;
            double predicted = (trendValue * 0.3 + seasonalValue * 0.7) * (1 + noise);

            double stdDev = calculateStandardDeviation(values);
            double margin = 1.96 * stdDev;

            predictions.add(TimeSeriesPoint.builder()
                    .timestamp(timestamp)
                    .value(Math.max(0, predicted))
                    .upperBound(predicted + margin)
                    .lowerBound(Math.max(0, predicted - margin))
                    .build());
        }

        return predictions;
    }

    private double[] estimateTrend(double[] values) {
        int window = 5;
        double[] trend = new double[values.length];

        for (int i = 0; i < values.length; i++) {
            int start = Math.max(0, i - window);
            int end = Math.min(values.length, i + window + 1);
            double sum = 0;
            for (int j = start; j < end; j++) {
                sum += values[j];
            }
            trend[i] = sum / (end - start);
        }

        return trend;
    }

    private double[] estimateSeasonal(double[] values) {
        int period = 144;
        double[] seasonal = new double[values.length];

        for (int i = 0; i < values.length; i++) {
            int count = 0;
            double sum = 0;
            for (int j = i; j < values.length; j += period) {
                sum += values[j];
                count++;
            }
            seasonal[i] = count > 0 ? sum / count : values[i];
        }

        return seasonal;
    }

    private double calculateStandardDeviation(double[] values) {
        if (values.length == 0) return 0;

        double mean = 0;
        for (double v : values) {
            mean += v;
        }
        mean /= values.length;

        double variance = 0;
        for (double v : values) {
            variance += Math.pow(v - mean, 2);
        }
        variance /= values.length;

        return Math.sqrt(variance);
    }

    private double calculateConfidence(List<TimeSeriesPoint> historicalData) {
        if (historicalData.size() < 24) {
            return 0.6;
        }

        double[] values = historicalData.stream()
                .mapToDouble(TimeSeriesPoint::getValue)
                .toArray();

        double mean = 0;
        for (double v : values) {
            mean += v;
        }
        mean /= values.length;

        double variance = 0;
        for (double v : values) {
            variance += Math.pow(v - mean, 2);
        }
        variance /= values.length;

        double cv = Math.sqrt(variance) / mean;

        double dataConfidence = Math.min(1.0, historicalData.size() / 144.0);
        double stabilityConfidence = Math.max(0, 1 - cv);

        return dataConfidence * 0.5 + stabilityConfidence * 0.5;
    }

    public double calculatePredictedPeakQps(TrafficPrediction prediction) {
        return prediction.getPredictedData().stream()
                .mapToDouble(TimeSeriesPoint::getUpperBound)
                .max()
                .orElse(0);
    }
}
