package com.distid.metrics;

import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MetricsConfig {

    @Bean
    public IdMetrics idMetrics(MeterRegistry registry) {
        return new IdMetrics(registry);
    }
}
