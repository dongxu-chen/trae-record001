package com.example.deduplication.config;

import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class GatewayRoutesConfig {

    @Bean
    public RouteLocator routeLocator(RouteLocatorBuilder builder) {
        return builder.routes()
                .route("example-service", r -> r
                        .path("/api/**")
                        .filters(f -> f
                                .addResponseHeader("X-Gateway-Processed", "true")
                        )
                        .uri("http://localhost:8081")
                )
                .build();
    }
}
