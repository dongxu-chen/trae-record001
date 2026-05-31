package com.dlq.platform.analysis.prediction;

import com.dlq.platform.common.enums.MqTypeEnum;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterPredictionService {

    public static class TimeSeriesData {
        private LocalDateTime time;
        private long count;

        public TimeSeriesData(LocalDateTime time, long count) {
            this.time = time;
            this.count = count;
        }

        public LocalDateTime getTime() { return time; }
        public void setTime(LocalDateTime time) { this.time = time; }
        public long getCount() { return count; }
        public void setCount(long count) { this.count = count; }
    }

    public static class PredictionPoint {
        private LocalDateTime time;
        private double predicted;
        private double lowerBound;
        private double upperBound;
        private double confidence;

        public PredictionPoint(LocalDateTime time, double predicted, double lowerBound, double upperBound, double confidence) {
            this.time = time;
            this.predicted = predicted;
            this.lowerBound = lowerBound;
            this.upperBound = upperBound;
            this.confidence = confidence;
        }

        public LocalDateTime getTime() { return time; }
        public double getPredicted() { return predicted; }
        public double getLowerBound() { return lowerBound; }
        public double getUpperBound() { return upperBound; }
        public double getConfidence() { return confidence; }
    }

    public static class PredictionResult {
        private List<PredictionPoint> predictions;
        private Map<String, Object> metrics;
        private List<TimeSeriesData> historicalData;
        private String trend;
        private double growthRate;
        private long predictedTotal;

        public PredictionResult() {
            this.metrics = new HashMap<>();
        }

        public List<PredictionPoint> getPredictions() { return predictions; }
        public void setPredictions(List<PredictionPoint> predictions) { this.predictions = predictions; }
        public Map<String, Object> getMetrics() { return metrics; }
        public void setMetrics(Map<String, Object> metrics) { this.metrics = metrics; }
        public List<TimeSeriesData> getHistoricalData() { return historicalData; }
        public void setHistoricalData(List<TimeSeriesData> historicalData) { this.historicalData = historicalData; }
        public String getTrend() { return trend; }
        public void setTrend(String trend) { this.trend = trend; }
        public double getGrowthRate() { return growthRate; }
        public void setGrowthRate(double growthRate) { this.growthRate = growthRate; }
        public long getPredictedTotal() { return predictedTotal; }
        public void setPredictedTotal(long predictedTotal) { this.predictedTotal = predictedTotal; }
    }

    public PredictionResult predict(List<TimeSeriesData> historicalData, int forecastDays) {
        PredictionResult result = new PredictionResult();

        if (historicalData == null || historicalData.isEmpty()) {
            result.setPredictions(new ArrayList<>());
            result.setTrend("UNKNOWN");
            return result;
        }

        result.setHistoricalData(historicalData);

        List<TimeSeriesData> sortedData = historicalData.stream()
                .sorted(Comparator.comparing(TimeSeriesData::getTime))
                .collect(Collectors.toList());

        double[] values = sortedData.stream().mapToDouble(TimeSeriesData::getCount).toArray();
        LocalDateTime[] times = sortedData.stream().map(TimeSeriesData::getTime).toArray(LocalDateTime[]::new);

        double[] ma = calculateMovingAverage(values, 3);
        double trendSlope = calculateTrendSlope(values);

        String trend;
        if (trendSlope > 0.1) {
            trend = "INCREASING";
        } else if (trendSlope < -0.1) {
            trend = "DECREASING";
        } else {
            trend = "STABLE";
        }
        result.setTrend(trend);

        double growthRate = calculateGrowthRate(values);
        result.setGrowthRate(growthRate);

        List<PredictionPoint> predictions = generatePredictions(
                times, values, ma, trendSlope, forecastDays);
        result.setPredictions(predictions);

        long predictedTotal = Math.round(predictions.stream().mapToDouble(PredictionPoint::getPredicted).sum());
        result.setPredictedTotal(predictedTotal);

        Map<String, Object> metrics = new HashMap<>();
        metrics.put("historicalTotal", (long) values[0]);
        metrics.put("historicalAvg", Arrays.stream(values).average().orElse(0));
        metrics.put("historicalMax", (long) Arrays.stream(values).max().orElse(0));
        metrics.put("historicalMin", (long) Arrays.stream(values).min().orElse(0));
        metrics.put("trendSlope", trendSlope);
        metrics.put("forecastDays", forecastDays);
        metrics.put("dataPoints", historicalData.size());
        result.setMetrics(metrics);

        return result;
    }

    private double[] calculateMovingAverage(double[] values, int window) {
        double[] ma = new double[values.length];
        for (int i = 0; i < values.length; i++) {
            int start = Math.max(0, i - window + 1);
            double sum = 0;
            int count = 0;
            for (int j = start; j <= i; j++) {
                sum += values[j];
                count++;
            }
            ma[i] = sum / count;
        }
        return ma;
    }

    private double calculateTrendSlope(double[] values) {
        if (values.length < 2) return 0;

        int n = values.length;
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

        for (int i = 0; i < n; i++) {
            sumX += i;
            sumY += values[i];
            sumXY += i * values[i];
            sumX2 += i * i;
        }

        double slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        double avgY = sumY / n;

        return avgY > 0 ? slope / avgY : slope;
    }

    private double calculateGrowthRate(double[] values) {
        if (values.length < 2) return 0;

        double firstHalfAvg = Arrays.stream(values, 0, values.length / 2).average().orElse(0);
        double secondHalfAvg = Arrays.stream(values, values.length / 2, values.length).average().orElse(0);

        if (firstHalfAvg == 0) return 0;
        return (secondHalfAvg - firstHalfAvg) / firstHalfAvg;
    }

    private List<PredictionPoint> generatePredictions(
            LocalDateTime[] times, double[] values, double[] ma, double trendSlope, int forecastDays) {
        List<PredictionPoint> predictions = new ArrayList<>();

        if (values.length == 0) return predictions;

        double lastValue = values[values.length - 1];
        double lastMA = ma[ma.length - 1];
        LocalDateTime lastTime = times[times.length - 1];

        double baseline = (lastValue + lastMA) / 2;
        double stdDev = calculateStdDev(values);

        for (int i = 1; i <= forecastDays; i++) {
            LocalDateTime predictionTime = lastTime.plusDays(i);

            double seasonalFactor = calculateSeasonalFactor(predictionTime);
            double trendComponent = trendSlope * i * baseline;

            double predicted = Math.max(0, baseline + trendComponent) * seasonalFactor;

            double confidence = calculateConfidence(i, values.length, stdDev);
            double margin = stdDev * (1 + i * 0.1);

            double lowerBound = Math.max(0, predicted - margin);
            double upperBound = predicted + margin;

            predictions.add(new PredictionPoint(
                    predictionTime,
                    Math.round(predicted * 100.0) / 100.0,
                    Math.round(lowerBound * 100.0) / 100.0,
                    Math.round(upperBound * 100.0) / 100.0,
                    Math.round(confidence * 100.0) / 100.0
            ));
        }

        return predictions;
    }

    private double calculateSeasonalFactor(LocalDateTime time) {
        int dayOfWeek = time.getDayOfWeek().getValue();
        int hour = time.getHour();

        double weekendFactor = (dayOfWeek >= 6) ? 0.7 : 1.0;

        double hourFactor;
        if (hour >= 9 && hour <= 18) {
            hourFactor = 1.2;
        } else if (hour >= 22 || hour < 6) {
            hourFactor = 0.4;
        } else {
            hourFactor = 0.8;
        }

        return weekendFactor * hourFactor;
    }

    private double calculateStdDev(double[] values) {
        if (values.length == 0) return 0;
        double mean = Arrays.stream(values).average().orElse(0);
        double variance = Arrays.stream(values)
                .map(v -> Math.pow(v - mean, 2))
                .average().orElse(0);
        return Math.sqrt(variance);
    }

    private double calculateConfidence(int horizon, int dataPoints, double stdDev) {
        double baseConfidence = Math.min(1.0, dataPoints / 30.0);
        double horizonDecay = Math.max(0.3, 1.0 - horizon * 0.05);
        double variabilityFactor = stdDev > 0 ? Math.max(0.5, 1.0 - stdDev / 100.0) : 1.0;

        return baseConfidence * horizonDecay * variabilityFactor;
    }

    public Map<String, PredictionResult> predictByDimension(
            Map<String, List<TimeSeriesData>> dimensionData, int forecastDays) {
        Map<String, PredictionResult> results = new HashMap<>();
        for (Map.Entry<String, List<TimeSeriesData>> entry : dimensionData.entrySet()) {
            results.put(entry.getKey(), predict(entry.getValue(), forecastDays));
        }
        return results;
    }

    public Map<String, Object> generateForecastReport(PredictionResult result) {
        Map<String, Object> report = new HashMap<>();

        report.put("trend", result.getTrend());
        report.put("growthRate", String.format("%.2f%%", result.getGrowthRate() * 100));
        report.put("predictedTotal", result.getPredictedTotal());
        report.put("metrics", result.getMetrics());

        String alertLevel = "NORMAL";
        String alertMessage = null;

        if ("INCREASING".equals(result.getTrend()) && result.getGrowthRate() > 0.5) {
            alertLevel = "WARNING";
            alertMessage = "死信数量呈现快速增长趋势，请关注";
        } else if ("INCREASING".equals(result.getTrend()) && result.getGrowthRate() > 0.2) {
            alertLevel = "INFO";
            alertMessage = "死信数量呈现增长趋势";
        } else if ("DECREASING".equals(result.getTrend())) {
            alertMessage = "死信数量呈现下降趋势，情况好转";
        }

        report.put("alertLevel", alertLevel);
        report.put("alertMessage", alertMessage);

        List<Map<String, Object>> dailyPredictions = new ArrayList<>();
        for (PredictionPoint p : result.getPredictions()) {
            Map<String, Object> point = new HashMap<>();
            point.put("time", p.getTime().toString());
            point.put("predicted", p.getPredicted());
            point.put("lowerBound", p.getLowerBound());
            point.put("upperBound", p.getUpperBound());
            point.put("confidence", p.getConfidence());
            dailyPredictions.add(point);
        }
        report.put("dailyPredictions", dailyPredictions);

        return report;
    }
}
