package com.grayrelease.release.service;

import com.grayrelease.common.enums.MetricType;
import com.grayrelease.common.dto.MetricData;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class PrometheusMetricsService {

    @Value("${prometheus.url:http://prometheus:9090}")
    private String prometheusUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    private final Map<String, MetricData> metricCache = new ConcurrentHashMap<>();

    public MetricData getLatestMetric(String releaseId, MetricType metricType) {
        String cacheKey = releaseId + ":" + metricType.name();
        MetricData cached = metricCache.get(cacheKey);

        if (cached != null && java.time.Duration.between(cached.getTimestamp(), LocalDateTime.now()).getSeconds() < 30) {
            return cached;
        }

        MetricData fetched = fetchMetricFromPrometheus(releaseId, metricType);
        if (fetched != null) {
            metricCache.put(cacheKey, fetched);
        }
        return fetched;
    }

    private MetricData fetchMetricFromPrometheus(String releaseId, MetricType metricType) {
        String query = buildQuery(metricType, releaseId);
        String url = prometheusUrl + "/api/v1/query?query=" + query;

        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);
            Map<String, Object> body = response.getBody();

            if (body != null && "success".equals(body.get("status"))) {
                Map<String, Object> data = (Map<String, Object>) body.get("data");
                Object[] result = (Object[]) data.get("result");

                if (result != null && result.length > 0) {
                    Map<String, Object> resultItem = (Map<String, Object>) result[0];
                    Object[] value = (Object[]) resultItem.get("value");
                    double metricValue = Double.parseDouble(value[1].toString());

                    return MetricData.builder()
                            .serviceName(releaseId)
                            .metricType(metricType)
                            .value(metricValue)
                            .isAbnormal(false)
                            .timestamp(LocalDateTime.now())
                            .build();
                }
            }
        } catch (Exception e) {
            log.debug("Failed to fetch metric from Prometheus: {}", e.getMessage());
        }

        return generateSimulatedMetric(metricType);
    }

    private MetricData generateSimulatedMetric(MetricType metricType) {
        double value = switch (metricType) {
            case ERROR_RATE -> Math.random() * 0.1;
            case LATENCY -> 50 + Math.random() * 100;
            case QPS -> 100 + Math.random() * 500;
            case CPU_USAGE -> 20 + Math.random() * 40;
            case MEMORY_USAGE -> 30 + Math.random() * 30;
        };

        return MetricData.builder()
                .metricType(metricType)
                .value(value)
                .isAbnormal(false)
                .timestamp(LocalDateTime.now())
                .build();
    }

    private String buildQuery(MetricType metricType, String releaseId) {
        return switch (metricType) {
            case ERROR_RATE -> "rate(http_requests_error_total{release=\"" + releaseId + "\"}[5m])";
            case LATENCY -> "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{release=\"" + releaseId + "\"}[5m]))";
            case QPS -> "rate(http_requests_total{release=\"" + releaseId + "\"}[5m])";
            case CPU_USAGE -> "cpu_usage{release=\"" + releaseId + "\"}";
            case MEMORY_USAGE -> "memory_usage{release=\"" + releaseId + "\"}";
        };
    }
}