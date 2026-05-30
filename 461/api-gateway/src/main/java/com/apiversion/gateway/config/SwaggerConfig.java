package com.apiversion.gateway.config;

import lombok.RequiredArgsConstructor;
import org.springframework.cloud.gateway.config.GatewayProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.server.RequestPredicates;
import org.springframework.web.reactive.function.server.RouterFunction;
import org.springframework.web.reactive.function.server.RouterFunctions;
import org.springframework.web.reactive.function.server.ServerResponse;

import java.util.ArrayList;
import java.util.List;

@Configuration
@RequiredArgsConstructor
public class SwaggerConfig {

    private final GatewayProperties gatewayProperties;

    @Bean
    public RouterFunction<ServerResponse> swaggerRouterFunction() {
        return RouterFunctions.route(
                RequestPredicates.GET("/v3/api-docs/{service}")
                        .and(RequestPredicates.accept(MediaType.APPLICATION_JSON)),
                request -> {
                    String service = request.pathVariable("service");
                    String apiDocsPath = "/v3/api-docs";
                    return ServerResponse.temporaryRedirect(
                            java.net.URI.create("/" + service + apiDocsPath)
                    ).build();
                }
        );
    }

    @Bean
    public List<String> swaggerServices() {
        List<String> services = new ArrayList<>();
        gatewayProperties.getRoutes().forEach(route -> 
            services.add(route.getId())
        );
        return services;
    }
}
