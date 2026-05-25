package com.alert.service;

import com.alert.entity.AlertEvent;
import com.alert.entity.AlertPrediction;
import com.alert.enums.AlertSeverity;
import com.alert.repository.AlertEventRepository;
import com.alert.repository.AlertPredictionRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class AlertPredictionService {

    @Autowired
    private AlertEventRepository alertEventRepository;

    @Autowired
    private AlertPredictionRepository predictionRepository;

    @Autowired
    private WebSocketService webSocketService;

    @Scheduled(cron = "0 0 * * * ?")
    @Transactional
    public void generatePredictions() {
        log.info("开始生成告警预测...");
        
        List<AlertEvent> historicalAlerts = alertEventRepository.findAll().stream()
                .filter(a -> a.getCreateTime().isAfter(LocalDateTime.now().minusDays(7)))
                .collect(Collectors.toList());

        if (historicalAlerts.size() < 10) {
            log.info("历史数据不足，跳过预测");
            return;
        }

        Map<String, List<AlertEvent>> hostPatterns = detectHostPatterns(historicalAlerts);
        Map<String, List<AlertEvent>> sourcePatterns = detectSourcePatterns(historicalAlerts);

        for (Map.Entry<String, List<AlertEvent>> entry : hostPatterns.entrySet()) {
            analyzePatternAndPredict(entry.getKey(), "HOST", entry.getValue());
        }

        for (Map.Entry<String, List<AlertEvent>> entry : sourcePatterns.entrySet()) {
            analyzePatternAndPredict(entry.getKey(), "SOURCE", entry.getValue());
        }
    }

    private Map<String, List<AlertEvent>> detectHostPatterns(List<AlertEvent> alerts) {
        Map<String, List<AlertEvent>> hostAlerts = alerts.stream()
                .filter(a -> a.getHost() != null && !a.getHost().isEmpty())
                .collect(Collectors.groupingBy(AlertEvent::getHost));

        return hostAlerts.entrySet().stream()
                .filter(e -> e.getValue().size() >= 5)
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    private Map<String, List<AlertEvent>> detectSourcePatterns(List<AlertEvent> alerts) {
        Map<String, List<AlertEvent>> sourceAlerts = alerts.stream()
                .filter(a -> a.getSource() != null && !a.getSource().isEmpty())
                .collect(Collectors.groupingBy(AlertEvent::getSource));

        return sourceAlerts.entrySet().stream()
                .filter(e -> e.getValue().size() >= 10)
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    private void analyzePatternAndPredict(String key, String type, List<AlertEvent> alerts) {
        Map<Integer, Long> hourlyDistribution = alerts.stream()
                .collect(Collectors.groupingBy(
                        a -> a.getCreateTime().getHour(),
                        Collectors.counting()
                ));

        int[] peakHours = findPeakHours(hourlyDistribution);
        if (peakHours.length == 0) return;

        double probability = calculatePredictionProbability(alerts, hourlyDistribution);

        if (probability >= 0.5) {
            for (int hour : peakHours) {
                AlertPrediction prediction = new AlertPrediction();
                prediction.setPredictionId(UUID.randomUUID().toString().replace("-", ""));
                prediction.setTitle(type + "告警预测: " + key);
                prediction.setDescription(String.format("基于过去7天模式分析，预测在%d点左右可能发生告警（模式匹配度: %.0f%%）",
                        hour, probability * 100));

                AlertSeverity avgSeverity = calculateAverageSeverity(alerts);
                prediction.setPredictedSeverity(avgSeverity.getCode());
                prediction.setProbability(probability);

                LocalDateTime predictedTime = calculateNextPredictionTime(hour);
                prediction.setPredictedTime(predictedTime);
                prediction.setPredictionWindowMinutes(60);

                if ("HOST".equals(type)) {
                    prediction.setHostPattern(key);
                } else {
                    prediction.setSourcePattern(key);
                }

                prediction.setStatus("PREDICTED");
                prediction = predictionRepository.save(prediction);

                Map<String, Object> message = new HashMap<>();
                message.put("type", "PREDICTION");
                message.put("data", prediction);
                webSocketService.broadcastAlert(message);

                log.info("生成预测: {} (概率: {}, 时间: {})", 
                        prediction.getTitle(), probability, predictedTime);
            }
        }
    }

    private int[] findPeakHours(Map<Integer, Long> hourlyDistribution) {
        if (hourlyDistribution.isEmpty()) return new int[0];

        long maxCount = Collections.max(hourlyDistribution.values());
        long avgCount = (long) hourlyDistribution.values().stream()
                .mapToLong(Long::longValue)
                .average()
                .orElse(0);

        List<Integer> peakHours = new ArrayList<>();
        for (Map.Entry<Integer, Long> entry : hourlyDistribution.entrySet()) {
            if (entry.getValue() >= avgCount * 1.5 && entry.getValue() >= 3) {
                peakHours.add(entry.getKey());
            }
        }

        return peakHours.stream().mapToInt(Integer::intValue).toArray();
    }

    private double calculatePredictionProbability(List<AlertEvent> alerts, Map<Integer, Long> hourlyDistribution) {
        double score = 0.0;

        int dataPoints = alerts.size();
        if (dataPoints >= 50) score += 0.4;
        else if (dataPoints >= 20) score += 0.3;
        else if (dataPoints >= 10) score += 0.2;

        long highSeverityCount = alerts.stream()
                .filter(a -> a.getSeverity() == AlertSeverity.CRITICAL || a.getSeverity() == AlertSeverity.MAJOR)
                .count();
        if (highSeverityCount >= 10) score += 0.2;
        else if (highSeverityCount >= 5) score += 0.1;

        long distinctDays = alerts.stream()
                .map(a -> a.getCreateTime().toLocalDate())
                .distinct()
                .count();
        if (distinctDays >= 5) score += 0.2;
        else if (distinctDays >= 3) score += 0.1;

        double variance = calculateHourlyVariance(hourlyDistribution);
        if (variance > 10) score += 0.2;
        else if (variance > 5) score += 0.1;

        return Math.min(score, 1.0);
    }

    private double calculateHourlyVariance(Map<Integer, Long> hourlyDistribution) {
        if (hourlyDistribution.size() < 2) return 0;

        double mean = hourlyDistribution.values().stream()
                .mapToLong(Long::longValue)
                .average()
                .orElse(0);

        return hourlyDistribution.values().stream()
                .mapToDouble(v -> Math.pow(v - mean, 2))
                .average()
                .orElse(0);
    }

    private AlertSeverity calculateAverageSeverity(List<AlertEvent> alerts) {
        double avgLevel = alerts.stream()
                .mapToInt(a -> a.getSeverity().getLevel())
                .average()
                .orElse(3);

        int level = (int) Math.round(avgLevel);
        for (AlertSeverity s : AlertSeverity.values()) {
            if (s.getLevel() == level) return s;
        }
        return AlertSeverity.MINOR;
    }

    private LocalDateTime calculateNextPredictionTime(int targetHour) {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime predictionTime = now.withHour(targetHour).withMinute(0).withSecond(0);

        if (predictionTime.isBefore(now)) {
            predictionTime = predictionTime.plusDays(1);
        }

        return predictionTime;
    }

    public List<AlertPrediction> getAllPredictions() {
        return predictionRepository.findActivePredictions(LocalDateTime.now());
    }

    public AlertPrediction getPredictionById(String predictionId) {
        return predictionRepository.findByPredictionId(predictionId)
                .orElseThrow(() -> new RuntimeException("预测不存在: " + predictionId));
    }

    @Transactional
    public AlertPrediction confirmPrediction(String predictionId, String actualAlertId) {
        AlertPrediction prediction = getPredictionById(predictionId);
        prediction.setStatus("CONFIRMED");
        prediction.setActualAlertId(actualAlertId);
        return predictionRepository.save(prediction);
    }

    @Transactional
    public AlertPrediction dismissPrediction(String predictionId) {
        AlertPrediction prediction = getPredictionById(predictionId);
        prediction.setStatus("DISMISSED");
        return predictionRepository.save(prediction);
    }
}
