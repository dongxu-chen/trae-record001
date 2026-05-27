package com.grayrelease.release.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class TrafficRoutingService {

    @Value("${kafka.topics.traffic-update:traffic-update}")
    private String trafficUpdateTopic;

    @Value("${routing.use-k8s-weighted:true}")
    private boolean useK8sWeightedRouting;

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final K8sWeightedRoutingService k8sWeightedRoutingService;

    public void updateTrafficSplit(String serviceName, String stableVersion, String canaryVersion, int canaryWeight) {
        log.info("Traffic split update: service={}, stable={}, canary={}, weight={}%",
                serviceName, stableVersion, canaryVersion, canaryWeight);

        if (useK8sWeightedRouting) {
            boolean success = k8sWeightedRoutingService.updateWeightedRouting(
                    serviceName, stableVersion, canaryVersion, canaryWeight
            );
            if (!success) {
                log.warn("K8s weighted routing failed, falling back to Kafka-based routing");
                publishKafkaMessage(serviceName, stableVersion, canaryVersion, canaryWeight, null);
            }
        } else {
            publishKafkaMessage(serviceName, stableVersion, canaryVersion, canaryWeight, null);
        }
    }

    public void updateABTestRouting(String serviceName, String stableVersion, String canaryVersion,
                                     java.util.Map<String, String> matchRules) {
        log.info("A/B test routing update: service={}, matchRules={}", serviceName, matchRules);

        if (useK8sWeightedRouting) {
            k8sWeightedRoutingService.updateWeightedRouting(
                    serviceName, stableVersion, canaryVersion, 50
            );
        }

        StringBuilder rulesJson = new StringBuilder("{");
        boolean first = true;
        for (java.util.Map.Entry<String, String> entry : matchRules.entrySet()) {
            if (!first) rulesJson.append(",");
            rulesJson.append("\"").append(entry.getKey()).append("\":\"").append(entry.getValue()).append("\"");
            first = false;
        }
        rulesJson.append("}");

        publishKafkaMessage(serviceName, stableVersion, canaryVersion, 50, matchRules);
    }

    public void switchToGreen(String serviceName, String stableVersion, String canaryVersion) {
        log.info("Blue-green switch to green: service={}", serviceName);

        if (useK8sWeightedRouting) {
            k8sWeightedRoutingService.updateWeightedRouting(
                    serviceName, stableVersion, canaryVersion, 100
            );
        }

        publishKafkaMessage(serviceName, stableVersion, canaryVersion, 100, null);
    }

    public void switchToBlue(String serviceName, String stableVersion, String canaryVersion) {
        log.info("Blue-green switch to blue: service={}", serviceName);

        if (useK8sWeightedRouting) {
            k8sWeightedRoutingService.updateWeightedRouting(
                    serviceName, stableVersion, canaryVersion, 0
            );
        }

        publishKafkaMessage(serviceName, stableVersion, canaryVersion, 0, null);
    }

    public K8sWeightedRoutingService.WeightedRouteStatus getRouteStatus(String serviceName) {
        return k8sWeightedRoutingService.getRouteStatus(serviceName);
    }

    private void publishKafkaMessage(String serviceName, String stableVersion, String canaryVersion,
                                      int canaryWeight, java.util.Map<String, String> matchRules) {
        StringBuilder message = new StringBuilder("{");
        message.append("\"serviceName\":\"").append(serviceName).append("\",");
        message.append("\"stableVersion\":\"").append(stableVersion).append("\",");
        message.append("\"canaryVersion\":\"").append(canaryVersion).append("\",");
        message.append("\"canaryWeight\":").append(canaryWeight);

        if (matchRules != null && !matchRules.isEmpty()) {
            message.append(",\"matchRules\":{");
            boolean first = true;
            for (java.util.Map.Entry<String, String> entry : matchRules.entrySet()) {
                if (!first) message.append(",");
                message.append("\"").append(entry.getKey()).append("\":\"").append(entry.getValue()).append("\"");
                first = false;
            }
            message.append("}");
        }

        message.append("}");

        try {
            kafkaTemplate.send(trafficUpdateTopic, message.toString());
        } catch (Exception e) {
            log.warn("Failed to publish traffic update to Kafka, using in-memory routing: {}", e.getMessage());
            TrafficRouterRegistry.updateRouting(message.toString());
        }
    }
}