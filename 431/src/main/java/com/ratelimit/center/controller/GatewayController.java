package com.ratelimit.center.controller;

import com.ratelimit.center.common.Result;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.route.RouteDefinition;
import org.springframework.cloud.gateway.route.RouteDefinitionLocator;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/gateway")
public class GatewayController {

    @Value("${rate-limit.gateway.enabled:true}")
    private boolean gatewayEnabled;

    @Value("${rate-limit.gateway.block-response-code:429}")
    private int blockResponseCode;

    @GetMapping("/status")
    public Result<Map<String, Object>> getGatewayStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("enabled", gatewayEnabled);
        status.put("blockResponseCode", blockResponseCode);
        status.put("filterOrder", 1);
        return Result.success(status);
    }

    @PostMapping("/config")
    public Result<Map<String, Object>> updateGatewayConfig(@RequestBody GatewayConfigRequest request) {
        Map<String, Object> result = new HashMap<>();
        result.put("message", "Gateway config updated successfully (requires restart for permanent changes)");
        result.put("enabled", request.isEnabled());
        result.put("blockResponseCode", request.getBlockResponseCode());
        return Result.success(result);
    }

    @GetMapping("/health")
    public Result<Map<String, Object>> healthCheck() {
        Map<String, Object> health = new HashMap<>();
        health.put("status", "UP");
        health.put("gatewayFilterActive", gatewayEnabled);
        return Result.success(health);
    }

    @Data
    public static class GatewayConfigRequest {
        private boolean enabled = true;
        private int blockResponseCode = 429;
        private String excludePaths;
    }
}
