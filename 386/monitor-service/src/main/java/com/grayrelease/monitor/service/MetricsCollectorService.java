package com.grayrelease.monitor.service;

import com.grayrelease.common.dto.MetricData;
import com.grayrelease.common.enums.MetricType;
import com.grayrelease.common.model.MetricThreshold;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class MetricsCollectorService {

    private final PrometheusQueryService prometheusQueryService;
    private final AnomalyDetectionService anomalyDetectionService;
    private final KafkaTemplate<String, String> kafkaTemplate;

    @Value("${kafka.topics.metrics-alert:metrics-alert}")
    private String metricsAlertTopic;

    private final Map<String, MonitoredTarget> monitoredTargets = new ConcurrentHashMap<>();

    public void registerTarget(String targetId, String serviceName, String version,
                                List<MetricThreshold> thresholds) {
        MonitoredTarget target = new MonitoredTarget(serviceName, version, thresholds);
        monitoredTargets.put(targetId, target);
        log.info("Registered monitored target: id={}, service={}, version={}", targetId, serviceName, version);
    }

    public void unregisterTarget(String targetId) {
        monitoredTargets.remove(targetId);
        log.info("Unregistered monitored target: id={}", targetId);
    }

    @Scheduled(fixedRate = 15000)
    public void collectMetrics() {
        for (Map.Entry<String, MonitoredTarget> entry : monitoredTargets.entrySet()) {
            String targetId = entry.getKey();
            MonitoredTarget target = entry.getValue();

            try {
                for (MetricThreshold threshold : target.getThresholds()) {
                    MetricData metricData = anomalyDetectionService.checkMetric(
                            target.getServiceName(),
                            target.getVersion(),
                            threshold.getMetricType(),
                            threshold
                    );

                    if (metricData != null && metricData.getIsAbnormal()) {
                        String alertMessage = String.format(
                                "{\"targetId\":\"%s\",\"serviceName\":\"%s\",\"version\":\"%s\",\"metricType\":\"%s\",\"value\":%.2f,\"threshold\":%.2f,\"timestamp\":\"%s\"}",
                                targetId, target.getServiceName(), target.getVersion(),
                                metricData.getMetricType(), metricData.getValue(),
                                threshold.getCriticalThreshold(), metricData.getTimestamp()
                        );

                        kafkaTemplate.send(metricsAlertTopic, alertMessage);
                        log.warn("Metrics alert sent: target={}, metric={}, value={}",
                                targetId, metricData.getMetricType(), metricData.getValue());
                    }
                }
            } catch (Exception e) {
                log.error("Error collecting metrics for target: {}", targetId, e);
            }
        }
    }

    public MetricData getLatestMetric(String serviceName, String version, MetricType metricType) {
        MetricThreshold defaultThreshold = MetricThreshold.builder()
                .metricType(metricType)
                .criticalThreshold(getDefaultThreshold(metricType))
                .comparison("gt")
                .durationSeconds(60)
                .build();

        return anomalyDetectionService.checkMetric(serviceName, version, metricType, defaultThreshold);
    }

    private double getDefaultThreshold(MetricType metricType) {
        return switch (metricType) {
            case ERROR_RATE -> 0.05;
            case LATENCY -> 1000.0;
            case QPS -> 10000.0;
            case CPU_USAGE -> 80.0;
            case MEMORY_USAGE -> 85.0;
        };
    }

    @lombok.Data
    @lombok.AllArgsConstructor
    private static class MonitoredTarget {
        private String serviceName;
        private String version;
        private List<MetricThreshold> thresholds;
    }
}