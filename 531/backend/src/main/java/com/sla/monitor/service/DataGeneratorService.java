package com.sla.monitor.service;

import com.sla.monitor.engine.PrometheusMetricsCollector;
import com.sla.monitor.engine.SlidingWindowMetrics;
import com.sla.monitor.model.ServiceInfo;
import com.sla.monitor.repository.ServiceInfoRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

@Service
public class DataGeneratorService {

    private static final Logger logger = LoggerFactory.getLogger(DataGeneratorService.class);

    private final PrometheusMetricsCollector metricsCollector;
    private final ServiceInfoRepository serviceInfoRepository;
    private final SlidingWindowMetrics slidingWindowMetrics;
    private final Random random = new Random();

    public DataGeneratorService(PrometheusMetricsCollector metricsCollector,
                                ServiceInfoRepository serviceInfoRepository,
                                SlidingWindowMetrics slidingWindowMetrics) {
        this.metricsCollector = metricsCollector;
        this.serviceInfoRepository = serviceInfoRepository;
        this.slidingWindowMetrics = slidingWindowMetrics;
    }

    public void generateRequests(String serviceName, int count) {
        ServiceInfo service = serviceInfoRepository.findByServiceName(serviceName).orElse(null);
        if (service == null) {
            logger.warn("Service not found: {}", serviceName);
            return;
        }

        for (int i = 0; i < count; i++) {
            boolean success = generateSuccess(serviceName);
            long latency = generateLatency(serviceName);
            metricsCollector.recordRequest(serviceName, latency, success);
        }
        
        logger.info("Generated {} requests for {}", count, serviceName);
    }

    private boolean generateSuccess(String serviceName) {
        double errorRate = getServiceErrorRate(serviceName);
        return random.nextDouble() * 100 > errorRate;
    }

    private long generateLatency(String serviceName) {
        long baseLatency = getServiceBaseLatency(serviceName);
        double variation = 0.3;
        
        if (random.nextDouble() < 0.05) {
            return baseLatency * 3 + random.nextLong() % 1000;
        }
        
        long latency = (long) (baseLatency * (1 + (random.nextDouble() - 0.5) * variation));
        return Math.max(10, latency);
    }

    private double getServiceErrorRate(String serviceName) {
        return switch (serviceName) {
            case "user-service" -> 0.5 + random.nextDouble() * 1.5;
            case "order-service" -> 1.0 + random.nextDouble() * 2.0;
            case "payment-service" -> 0.3 + random.nextDouble() * 0.7;
            case "inventory-service" -> 2.0 + random.nextDouble() * 3.0;
            default -> 1.0;
        };
    }

    private long getServiceBaseLatency(String serviceName) {
        return switch (serviceName) {
            case "user-service" -> 150;
            case "order-service" -> 250;
            case "payment-service" -> 400;
            case "inventory-service" -> 200;
            default -> 200;
        };
    }

    public void generateHistoricalData() {
        List<String> serviceNames = new ArrayList<>();
        serviceNames.add("user-service");
        serviceNames.add("order-service");
        serviceNames.add("payment-service");
        serviceNames.add("inventory-service");

        for (String serviceName : serviceNames) {
            for (int i = 0; i < 500; i++) {
                boolean success = generateSuccess(serviceName);
                long latency = generateLatency(serviceName);
                slidingWindowMetrics.recordRequest(serviceName, latency, success);
            }
            logger.info("Generated historical data for {}", serviceName);
        }
    }
}
