package com.sla.monitor.controller;

import com.sla.monitor.model.ServiceDependency;
import com.sla.monitor.repository.ServiceInfoRepository;
import com.sla.monitor.service.SlaPropagationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/dependencies")
public class ServiceDependencyController {

    private final SlaPropagationService propagationService;
    private final ServiceInfoRepository serviceInfoRepository;

    public ServiceDependencyController(SlaPropagationService propagationService,
                                        ServiceInfoRepository serviceInfoRepository) {
        this.propagationService = propagationService;
        this.serviceInfoRepository = serviceInfoRepository;
    }

    @GetMapping
    public List<ServiceDependency> getAllDependencies() {
        return propagationService.getAllDependencies();
    }

    @GetMapping("/service/{serviceName}")
    public ResponseEntity<Map<String, Object>> getServiceDependencies(@PathVariable String serviceName) {
        List<ServiceDependency> upstream = propagationService.getUpstreamDependencies(serviceName);
        List<ServiceDependency> downstream = propagationService.getDownstreamDependencies(serviceName);
        
        return ResponseEntity.ok(Map.of(
            "upstreamDependencies", upstream,
            "downstreamDependencies", downstream,
            "upstreamCount", upstream.size(),
            "downstreamCount", downstream.size()
        ));
    }

    @GetMapping("/upstream/{serviceName}")
    public List<ServiceDependency> getUpstreamDependencies(@PathVariable String serviceName) {
        return propagationService.getUpstreamDependencies(serviceName);
    }

    @GetMapping("/downstream/{serviceName}")
    public List<ServiceDependency> getDownstreamDependencies(@PathVariable String serviceName) {
        return propagationService.getDownstreamDependencies(serviceName);
    }

    @PostMapping
    public ResponseEntity<?> addDependency(@RequestBody ServiceDependency dependency) {
        try {
            ServiceDependency saved = propagationService.addDependency(dependency);
            return ResponseEntity.ok(saved);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> removeDependency(@PathVariable Long id) {
        propagationService.removeDependency(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/analyze/{serviceName}")
    public ResponseEntity<?> analyzePropagation(@PathVariable String serviceName) {
        return serviceInfoRepository.findByServiceName(serviceName)
                .map(service -> {
                    SlaPropagationService.PropagationResult result = 
                        propagationService.analyzeServicePropagation(service);
                    if (result != null) {
                        return ResponseEntity.ok(result);
                    }
                    return ResponseEntity.noContent().build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/graph")
    public ResponseEntity<Map<String, Object>> getDependencyGraph() {
        List<ServiceDependency> allDependencies = propagationService.getAllDependencies();
        
        List<Map<String, String>> edges = allDependencies.stream()
                .map(d -> Map.of(
                    "from", d.getUpstreamService(),
                    "to", d.getDownstreamService(),
                    "type", d.getDependencyType().name(),
                    "impact", d.getImpactLevel().name(),
                    "weight", String.valueOf(d.getSlaImpactFactor())
                ))
                .toList();

        List<String> nodes = allDependencies.stream()
                .flatMap(d -> List.of(d.getUpstreamService(), d.getDownstreamService()).stream())
                .distinct()
                .toList();

        return ResponseEntity.ok(Map.of(
            "nodes", nodes,
            "edges", edges,
            "totalDependencies", allDependencies.size()
        ));
    }

    @GetMapping("/risk-analysis")
    public ResponseEntity<Map<String, Object>> getRiskAnalysis() {
        List<ServiceDependency> criticalDependencies = propagationService.getAllDependencies()
                .stream()
                .filter(d -> d.getImpactLevel() == ServiceDependency.ImpactLevel.CRITICAL)
                .toList();

        List<ServiceDependency> highDependencies = propagationService.getAllDependencies()
                .stream()
                .filter(d -> d.getImpactLevel() == ServiceDependency.ImpactLevel.HIGH)
                .toList();

        return ResponseEntity.ok(Map.of(
            "criticalDependencies", criticalDependencies.size(),
            "highImpactDependencies", highDependencies.size(),
            "totalDependencies", propagationService.getAllDependencies().size(),
            "criticalDependenciesList", criticalDependencies
        ));
    }
}
