package com.gateway.config;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Configuration
@RequiredArgsConstructor
public class CircuitBreakerConfiguration {

    private final GatewayProperties gatewayProperties;

    @Bean
    public CircuitBreakerRegistry circuitBreakerRegistry() {
        GatewayProperties.CircuitBreaker cbProps = gatewayProperties.getCircuitBreaker();

        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
                .failureRateThreshold(cbProps.getFailureRateThreshold())
                .waitDurationInOpenState(Duration.ofSeconds(cbProps.getWaitDurationInOpenState()))
                .permittedNumberOfCallsInHalfOpenState(cbProps.getPermittedCallsInHalfOpenState())
                .slidingWindowSize(cbProps.getSlidingWindowSize())
                .minimumNumberOfCalls(cbProps.getMinimumNumberOfCalls())
                .slowCallDurationThreshold(Duration.ofMillis(cbProps.getSlowCallDurationThreshold()))
                .slowCallRateThreshold(cbProps.getSlowCallRateThreshold())
                .automaticTransitionFromOpenToHalfOpenEnabled(true)
                .build();

        return CircuitBreakerRegistry.of(config);
    }

    @Bean
    public Map<String, CircuitBreaker> circuitBreakerMap(CircuitBreakerRegistry registry) {
        Map<String, CircuitBreaker> map = new HashMap<>();

        String[] serviceIds = {"user-service", "order-service", "payment-service", "admin-service"};
        for (String serviceId : serviceIds) {
            map.put(serviceId, registry.circuitBreaker(serviceId));
        }

        return map;
    }
}
