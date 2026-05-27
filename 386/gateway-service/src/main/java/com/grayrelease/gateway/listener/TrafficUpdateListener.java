package com.grayrelease.gateway.listener;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.grayrelease.gateway.registry.TrafficRoutingRegistry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class TrafficUpdateListener {

    private final TrafficRoutingRegistry routingRegistry;
    private final ObjectMapper objectMapper;

    @Value("${kubernetes.service-suffix:svc.cluster.local}")
    private String serviceSuffix;

    @KafkaListener(topics = "${kafka.topics.traffic-update:traffic-update}", groupId = "gateway-service")
    public void onTrafficUpdate(String message) {
        try {
            Map<String, Object> data = objectMapper.readValue(message, Map.class);

            String serviceName = (String) data.get("serviceName");
            String stableVersion = (String) data.get("stableVersion");
            String canaryVersion = (String) data.get("canaryVersion");
            int canaryWeight = data.get("canaryWeight") != null ?
                    ((Number) data.get("canaryWeight")).intValue() : 0;

            @SuppressWarnings("unchecked")
            Map<String, String> matchRules = (Map<String, String>) data.get("matchRules");

            TrafficRoutingRegistry.RoutingConfig config = new TrafficRoutingRegistry.RoutingConfig();
            config.setServiceName(serviceName);
            config.setStableVersion(stableVersion);
            config.setCanaryVersion(canaryVersion);
            config.setCanaryWeight(canaryWeight);
            config.setStableHost(serviceName + "-stable." + serviceSuffix);
            config.setStablePort(8080);
            config.setCanaryHost(serviceName + "-canary." + serviceSuffix);
            config.setCanaryPort(8080);
            config.setMatchRules(matchRules);

            routingRegistry.updateRouting(serviceName, config);

            log.info("Traffic update processed: service={}, stable={}, canary={}, weight={}%",
                    serviceName, stableVersion, canaryVersion, canaryWeight);
        } catch (Exception e) {
            log.error("Failed to process traffic update message", e);
        }
    }
}