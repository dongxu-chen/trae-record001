package com.apiversion.gateway.config;

import lombok.RequiredArgsConstructor;
import org.springframework.cloud.gateway.config.GatewayProperties;
import org.springframework.cloud.gateway.route.RouteDefinition;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.server.RequestPredicates;
import org.springframework.web.reactive.function.server.RouterFunction;
import org.springframework.web.reactive.function.server.RouterFunctions;
import org.springframework.web.reactive.function.server.ServerResponse;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Configuration
@RequiredArgsConstructor
public class OpenApiResourceConfig {

    private final GatewayProperties gatewayProperties;

    @Bean
    public RouterFunction<ServerResponse> openApiResources() {
        return RouterFunctions.route(
                RequestPredicates.GET("/v3/api-docs/swagger-config")
                        .and(RequestPredicates.accept(MediaType.APPLICATION_JSON)),
                request -> {
                    Map<String, Object> config = new HashMap<>();
                    List<Map<String, String>> urls = new ArrayList<>();

                    for (RouteDefinition route : gatewayProperties.getRoutes()) {
                        if (route.getId().contains("swagger") || route.getId().contains("api-docs")) {
                            continue;
                        }
                        Map<String, String> urlEntry = new HashMap<>();
                        urlEntry.put("name", route.getId());
                        urlEntry.put("url", "/v3/api-docs/" + route.getId());
                        urls.add(urlEntry);
                    }

                    config.put("urls", urls);
                    config.put("configUrl", "/v3/api-docs/swagger-config");
                    config.put("oauth2RedirectUrl", "/webjars/swagger-ui/oauth2-redirect.html");
                    config.put("validatorUrl", "");

                    return ServerResponse.ok()
                            .contentType(MediaType.APPLICATION_JSON)
                            .bodyValue(config);
                }
        );
    }

    @Bean
    public RouterFunction<ServerResponse> openApiDocsByService() {
        return RouterFunctions.route(
                RequestPredicates.GET("/v3/api-docs/{serviceId}")
                        .and(RequestPredicates.accept(MediaType.ALL)),
                request -> {
                    String serviceId = request.pathVariable("serviceId");
                    return gatewayProperties.getRoutes().stream()
                            .filter(route -> route.getId().equals(serviceId))
                            .findFirst()
                            .map(route -> {
                                String predicate = route.getPredicates().get(0).getArgs()
                                        .values().iterator().next();
                                String pathPrefix = predicate.replace("/**", "");
                                return ServerResponse.temporaryRedirect(
                                        java.net.URI.create(pathPrefix + "/v3/api-docs")
                                ).build();
                            })
                            .orElse(ServerResponse.notFound().build());
                }
        );
    }
}
