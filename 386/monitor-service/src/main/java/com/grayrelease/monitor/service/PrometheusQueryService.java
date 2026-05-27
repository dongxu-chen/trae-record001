package com.grayrelease.monitor.service;

import com.grayrelease.common.enums.MetricType;
import com.grayrelease.common.dto.MetricData;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class PrometheusQueryService {

    @Value("${prometheus.url:http://prometheus:9090}")
    private String prometheusUrl;

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    public MetricData queryMetric(String serviceName, String version, MetricType metricType) {
        String query = buildQuery(metricType, serviceName, version);
        String url = prometheusUrl + "/api/v1/query?query=" + query;

        try {
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            JsonNode root = objectMapper.readTree(response.getBody());

            if ("success".equals(root.path("status").asText())) {
                JsonNode result = root.path("data").path("result");
                if (result.isArray() && result.size() > 0) {
                    double value = result.get(0).path("value").get(1).asDouble();

                    return MetricData.builder()
                            .serviceName(serviceName)
                            .version(version)
                            .metricType(metricType)
                            .value(value)
                            .isAbnormal(false)
                            .timestamp(LocalDateTime.now())
                            .build();
                }
            }
        } catch (Exception e) {
            log.debug("Failed to query Prometheus for {}-{}: {}", serviceName, version, e.getMessage());
        }

        return null;
    }

    public List<MetricData> queryRangeMetric(String serviceName, String version,
                                              MetricType metricType, int minutes) {
        String query = buildQuery(metricType, serviceName, version);
        long end = System.currentTimeMillis() / 1000;
        long start = end - (minutes * 60L);
        String url = String.format("%s/api/v1/query_range?query=%s&start=%d&end=%d&step=30",
                prometheusUrl, query, start, end);

        List<MetricData> results = new ArrayList<>();

        try {
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            JsonNode root = objectMapper.readTree(response.getBody());

            if ("success".equals(root.path("status").asText())) {
                JsonNode result = root.path("data").path("result");
                if (result.isArray() && result.size() > 0) {
                    JsonNode values = result.get(0).path("values");
                    for (JsonNode value : values) {
                        double metricValue = value.get(1).asDouble();
                        long timestamp = value.get(0).asLong();

                        results.add(MetricData.builder()
                                .serviceName(serviceName)
                                .version(version)
                                .metricType(metricType)
                                .value(metricValue)
                                .isAbnormal(false)
                                .timestamp(LocalDateTime.now())
                                .build());
                    }
                }
            }
        } catch (Exception e) {
            log.debug("Failed to query range from Prometheus: {}", e.getMessage());
        }

        return results;
    }

    private String buildQuery(MetricType metricType, String serviceName, String version) {
        String labelSelector = String.format("{service=\"%s\",version=\"%s\"}", serviceName, version);

        return switch (metricType) {
            case ERROR_RATE -> "rate(http_requests_error_total" + labelSelector + "[5m])";
            case LATENCY -> "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket" + labelSelector + "[5m]))";
            case QPS -> "rate(http_requests_total" + labelSelector + "[5m])";
            case CPU_USAGE -> "cpu_usage" + labelSelector;
            case MEMORY_USAGE -> "memory_usage" + labelSelector;
        };
    }
}