package com.sla.monitor.service;

import com.sla.monitor.dto.PredictionResultDTO;
import com.sla.monitor.dto.SlaTrendDTO;
import com.sla.monitor.model.SlaMetrics;
import com.sla.monitor.repository.SlaMetricsRepository;
import org.apache.commons.math3.stat.regression.SimpleRegression;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class TimeSeriesPredictionService {

    private static final Logger logger = LoggerFactory.getLogger(TimeSeriesPredictionService.class);

    private final SlaMetricsRepository slaMetricsRepository;

    @Value("${sla.prediction.forecast-points:24}")
    private int forecastPoints;

    @Value("${sla.prediction.historical-data-hours:24}")
    private int historicalDataHours;

    public TimeSeriesPredictionService(SlaMetricsRepository slaMetricsRepository) {
        this.slaMetricsRepository = slaMetricsRepository;
    }

    public PredictionResultDTO predictSlaTrend(String serviceName) {
        LocalDateTime startTime = LocalDateTime.now().minusHours(historicalDataHours);
        List<SlaMetrics> historicalMetrics = slaMetricsRepository
                .findByServiceNameAndTimestampAfterOrderByTimestampAsc(serviceName, startTime);

        PredictionResultDTO result = new PredictionResultDTO();
        result.setServiceName(serviceName);

        List<SlaTrendDTO> historicalData = new ArrayList<>();
        for (SlaMetrics metric : historicalMetrics) {
            SlaTrendDTO dto = new SlaTrendDTO();
            dto.setTimestamp(metric.getTimestamp());
            dto.setValue(metric.getSlaAchievementRate());
            historicalData.add(dto);
        }
        result.setHistoricalData(historicalData);

        if (historicalMetrics.size() < 5) {
            result.setPredictedData(new ArrayList<>());
            result.setPredictedSlaRate(historicalMetrics.isEmpty() ? 100.0 : 
                    historicalMetrics.get(historicalMetrics.size() - 1).getSlaAchievementRate());
            result.setTrendDirection("INSUFFICIENT_DATA");
            result.setPredictedViolation(false);
            return result;
        }

        List<SlaTrendDTO> predictedData = performLinearRegressionPrediction(historicalMetrics);
        result.setPredictedData(predictedData);

        if (!predictedData.isEmpty()) {
            double lastPredicted = predictedData.get(predictedData.size() - 1).getValue();
            result.setPredictedSlaRate(lastPredicted);
            result.setPredictedViolation(lastPredicted < 95.0);

            double firstValue = historicalData.get(0).getValue();
            double lastValue = historicalData.get(historicalData.size() - 1).getValue();
            double change = lastValue - firstValue;
            
            if (Math.abs(change) < 1.0) {
                result.setTrendDirection("STABLE");
            } else if (change > 0) {
                result.setTrendDirection("IMPROVING");
            } else {
                result.setTrendDirection("DEGRADING");
            }
        }

        return result;
    }

    private List<SlaTrendDTO> performLinearRegressionPrediction(List<SlaMetrics> historicalMetrics) {
        SimpleRegression regression = new SimpleRegression();
        
        long baseTime = historicalMetrics.get(0).getTimestamp().atZone(java.time.ZoneId.systemDefault()).toEpochSecond();
        
        for (int i = 0; i < historicalMetrics.size(); i++) {
            SlaMetrics metric = historicalMetrics.get(i);
            long timeX = metric.getTimestamp().atZone(java.time.ZoneId.systemDefault()).toEpochSecond() - baseTime;
            regression.addData(timeX, metric.getSlaAchievementRate());
        }

        List<SlaTrendDTO> predictions = new ArrayList<>();
        LocalDateTime lastTime = historicalMetrics.get(historicalMetrics.size() - 1).getTimestamp();

        for (int i = 1; i <= forecastPoints; i++) {
            LocalDateTime predictedTime = lastTime.plusMinutes(i * 5);
            long timeX = predictedTime.atZone(java.time.ZoneId.systemDefault()).toEpochSecond() - baseTime;
            double predictedValue = regression.predict(timeX);

            SlaTrendDTO dto = new SlaTrendDTO();
            dto.setTimestamp(predictedTime);
            dto.setValue(Math.max(0.0, Math.min(100.0, predictedValue)));
            predictions.add(dto);
        }

        return predictions;
    }

    public double predictAvailability(String serviceName, LocalDateTime targetTime) {
        LocalDateTime startTime = LocalDateTime.now().minusHours(historicalDataHours);
        List<SlaMetrics> historicalMetrics = slaMetricsRepository
                .findByServiceNameAndTimestampAfterOrderByTimestampAsc(serviceName, startTime);

        if (historicalMetrics.size() < 5) {
            return historicalMetrics.isEmpty() ? 99.9 : 
                    historicalMetrics.get(historicalMetrics.size() - 1).getAvailability();
        }

        SimpleRegression regression = new SimpleRegression();
        long baseTime = historicalMetrics.get(0).getTimestamp().atZone(java.time.ZoneId.systemDefault()).toEpochSecond();

        for (SlaMetrics metric : historicalMetrics) {
            long timeX = metric.getTimestamp().atZone(java.time.ZoneId.systemDefault()).toEpochSecond() - baseTime;
            regression.addData(timeX, metric.getAvailability());
        }

        long targetX = targetTime.atZone(java.time.ZoneId.systemDefault()).toEpochSecond() - baseTime;
        double predicted = regression.predict(targetX);
        
        return Math.max(0.0, Math.min(100.0, predicted));
    }

    public double calculateTrendSlope(String serviceName) {
        LocalDateTime startTime = LocalDateTime.now().minusHours(historicalDataHours);
        List<SlaMetrics> historicalMetrics = slaMetricsRepository
                .findByServiceNameAndTimestampAfterOrderByTimestampAsc(serviceName, startTime);

        if (historicalMetrics.size() < 5) {
            return 0.0;
        }

        SimpleRegression regression = new SimpleRegression();
        long baseTime = historicalMetrics.get(0).getTimestamp().atZone(java.time.ZoneId.systemDefault()).toEpochSecond();

        for (SlaMetrics metric : historicalMetrics) {
            long timeX = metric.getTimestamp().atZone(java.time.ZoneId.systemDefault()).toEpochSecond() - baseTime;
            regression.addData(timeX, metric.getSlaAchievementRate());
        }

        return regression.getSlope();
    }
}
