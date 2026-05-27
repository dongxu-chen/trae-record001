package com.grayrelease.gateway.controller;

import com.grayrelease.gateway.registry.TrafficRoutingRegistry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/gateway")
@RequiredArgsConstructor
public class GatewayController {

    private final TrafficRoutingRegistry routingRegistry;

    @GetMapping("/routes")
    public ResponseEntity<Map<String, TrafficRoutingRegistry.RoutingConfig>> getRoutes() {
        return ResponseEntity.ok(routingRegistry.getAllRoutings());
    }

    @GetMapping("/routes/{serviceName}")
    public ResponseEntity<TrafficRoutingRegistry.RoutingConfig> getRoute(@PathVariable String serviceName) {
        TrafficRoutingRegistry.RoutingConfig config = routingRegistry.getRouting(serviceName);
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    @PostMapping("/routes")
    public ResponseEntity<String> updateRoute(@RequestBody TrafficRoutingRegistry.RoutingConfig config) {
        routingRegistry.updateRouting(config.getServiceName(), config);
        return ResponseEntity.ok("Route updated for service: " + config.getServiceName());
    }

    @DeleteMapping("/routes/{serviceName}")
    public ResponseEntity<String> deleteRoute(@PathVariable String serviceName) {
        routingRegistry.removeRouting(serviceName);
        return ResponseEntity.ok("Route removed for service: " + serviceName);
    }
}