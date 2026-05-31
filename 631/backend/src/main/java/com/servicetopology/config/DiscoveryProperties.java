package com.servicetopology.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.ArrayList;
import java.util.List;

@Data
@Configuration
@ConfigurationProperties(prefix = "discovery")
public class DiscoveryProperties {

    private KubernetesDiscovery kubernetes = new KubernetesDiscovery();
    private TracingProperties tracing = new TracingProperties();
    private AsyncCallDetection asyncCallDetection = new AsyncCallDetection();

    @Data
    public static class KubernetesDiscovery {
        private boolean enabled = true;
        private List<String> namespaces = new ArrayList<>(List.of("default"));
        private long scanInterval = 30000;
        private String serviceLabelSelector = "app";
    }

    @Data
    public static class TracingProperties {
        private boolean enabled = true;
        private String otlpEndpoint = "http://localhost:4317";
        private String serviceName = "service-topology-discovery";
        private MessageQueueDetection messageQueueDetection = new MessageQueueDetection();
    }

    @Data
    public static class MessageQueueDetection {
        private boolean enabled = true;
        private List<String> queuePrefixes = new ArrayList<>(List.of("kafka", "rabbitmq", "activemq", "redis"));
    }

    @Data
    public static class AsyncCallDetection {
        private boolean enabled = true;
        private List<String> asyncHeaders = new ArrayList<>(
            List.of("X-Async-Call", "X-Correlation-ID", "traceparent")
        );
    }
}
