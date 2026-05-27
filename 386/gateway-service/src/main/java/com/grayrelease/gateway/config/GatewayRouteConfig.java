package com.grayrelease.gateway.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Slf4j
@Configuration
public class GatewayRouteConfig {

    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        log.info("Initializing gateway route locator");
        return builder.routes()
                .route("default-route", r -> r
                        .path("/api/**")
                        .filters(f -> f.stripPrefix(1))
                        .uri("lb://default-service"))
                .build();
    }
}