package com.alert.service;

import com.alert.entity.AlertEvent;
import com.alert.entity.AlertRootCause;
import com.alert.enums.AlertSeverity;
import com.alert.enums.AlertStatus;
import com.alert.repository.AlertEventRepository;
import com.alert.repository.AlertRootCauseRepository;
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
public class RootCauseAnalysisService {

    @Autowired
    private AlertEventRepository alertEventRepository;

    @Autowired
    private AlertRootCauseRepository rootCauseRepository;

    @Autowired
    private WebSocketService webSocketService;

    @Scheduled(fixedRate = 300000)
    @Transactional
    public void analyzeRootCauses() {
        log.info("开始执行根因分析...");
        
        LocalDateTime timeWindow = LocalDateTime.now().minusHours(1);
        List<AlertEvent> recentAlerts = alertEventRepository.findAll().stream()
                .filter(a -> a.getCreateTime().isAfter(timeWindow))
                .filter(a -> a.getStatus() != AlertStatus.CLOSED && a.getStatus() != AlertStatus.SUPPRESSED)
                .collect(Collectors.toList());

        if (recentAlerts.size() < 3) {
            return;
        }

        Map<String, List<AlertEvent>> hostGroups = groupAlertsByHost(recentAlerts);
        Map<String, List<AlertEvent>> sourceGroups = groupAlertsBySource(recentAlerts);

        for (Map.Entry<String, List<AlertEvent>> entry : hostGroups.entrySet()) {
            if (entry.getValue().size() >= 3) {
                analyzeRootCause(entry.getKey(), "HOST", entry.getValue());
            }
        }

        for (Map.Entry<String, List<AlertEvent>> entry : sourceGroups.entrySet()) {
            if (entry.getValue().size() >= 5) {
                analyzeRootCause(entry.getKey(), "SOURCE", entry.getValue());
            }
        }
    }

    private Map<String, List<AlertEvent>> groupAlertsByHost(List<AlertEvent> alerts) {
        return alerts.stream()
                .filter(a -> a.getHost() != null && !a.getHost().isEmpty())
                .collect(Collectors.groupingBy(AlertEvent::getHost));
    }

    private Map<String, List<AlertEvent>> groupAlertsBySource(List<AlertEvent> alerts) {
        return alerts.stream()
                .filter(a -> a.getSource() != null && !a.getSource().isEmpty())
                .collect(Collectors.groupingBy(AlertEvent::getSource));
    }

    private void analyzeRootCause(String key, String type, List<AlertEvent> alerts) {
        AlertEvent earliestAlert = alerts.stream()
                .min(Comparator.comparing(AlertEvent::getCreateTime))
                .orElse(null);

        if (earliestAlert == null) return;

        AlertEvent highestSeverityAlert = alerts.stream()
                .max(Comparator.comparingInt(a -> a.getSeverity().getLevel()))
                .orElse(earliestAlert);

        double confidence = calculateConfidence(alerts, type);

        if (confidence >= 0.6) {
            AlertRootCause rootCause = new AlertRootCause();
            rootCause.setRootCauseId(UUID.randomUUID().toString().replace("-", ""));
            rootCause.setTitle(type + "级故障: " + key);
            rootCause.setDescription(String.format("检测到%s相关告警%d条，可能存在级联故障", type, alerts.size()));
            rootCause.setRootAlertId(highestSeverityAlert.getAlertId());
            rootCause.setConfidenceScore(confidence);
            rootCause.setStatus("ANALYZING");
            rootCause.setAnalysisTime(LocalDateTime.now());
            rootCause.setTags(type + ":" + key);
            rootCause.setAffectedCount(alerts.size());

            rootCause = rootCauseRepository.save(rootCause);
            
            Map<String, Object> message = new HashMap<>();
            message.put("type", "ROOT_CAUSE");
            message.put("data", rootCause);
            webSocketService.broadcastAlert(message);

            log.info("发现潜在根因: {} (置信度: {})", rootCause.getTitle(), confidence);
        }
    }

    private double calculateConfidence(List<AlertEvent> alerts, String type) {
        double score = 0.0;

        int size = alerts.size();
        if (size >= 10) score += 0.4;
        else if (size >= 5) score += 0.3;
        else if (size >= 3) score += 0.2;

        long criticalCount = alerts.stream()
                .filter(a -> a.getSeverity() == AlertSeverity.CRITICAL || a.getSeverity() == AlertSeverity.MAJOR)
                .count();
        if (criticalCount >= 3) score += 0.3;
        else if (criticalCount >= 1) score += 0.15;

        LocalDateTime firstTime = alerts.stream().map(AlertEvent::getCreateTime).min(LocalDateTime::compareTo).orElse(LocalDateTime.now());
        LocalDateTime lastTime = alerts.stream().map(AlertEvent::getCreateTime).max(LocalDateTime::compareTo).orElse(LocalDateTime.now());
        long minutes = java.time.Duration.between(firstTime, lastTime).toMinutes();
        if (minutes <= 15) score += 0.2;
        else if (minutes <= 30) score += 0.1;

        boolean hasDependency = alerts.stream()
                .anyMatch(a -> a.getParentAlertId() != null && !a.getParentAlertId().isEmpty());
        if (hasDependency) score += 0.1;

        return Math.min(score, 1.0);
    }

    public List<AlertRootCause> getAllRootCauses() {
        return rootCauseRepository.findAll();
    }

    public AlertRootCause getRootCauseById(String rootCauseId) {
        return rootCauseRepository.findByRootCauseId(rootCauseId)
                .orElseThrow(() -> new RuntimeException("根因分析不存在: " + rootCauseId));
    }

    @Transactional
    public AlertRootCause confirmRootCause(String rootCauseId) {
        AlertRootCause rootCause = getRootCauseById(rootCauseId);
        rootCause.setStatus("CONFIRMED");
        return rootCauseRepository.save(rootCause);
    }

    @Transactional
    public AlertRootCause rejectRootCause(String rootCauseId) {
        AlertRootCause rootCause = getRootCauseById(rootCauseId);
        rootCause.setStatus("REJECTED");
        return rootCauseRepository.save(rootCause);
    }

    public List<AlertEvent> getAffectedAlerts(String rootCauseId) {
        AlertRootCause rootCause = getRootCauseById(rootCauseId);
        String[] tags = rootCause.getTags().split(":");
        if (tags.length < 2) return Collections.emptyList();

        String type = tags[0];
        String value = tags[1];

        return alertEventRepository.findAll().stream()
                .filter(a -> {
                    if ("HOST".equals(type)) {
                        return value.equals(a.getHost());
                    } else if ("SOURCE".equals(type)) {
                        return value.equals(a.getSource());
                    }
                    return false;
                })
                .collect(Collectors.toList());
    }
}
