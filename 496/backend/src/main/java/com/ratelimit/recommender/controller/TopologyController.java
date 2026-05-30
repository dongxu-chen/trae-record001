package com.ratelimit.recommender.controller;

import com.ratelimit.recommender.model.*;
import com.ratelimit.recommender.service.TopologyAnalysisService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/topology")
@CrossOrigin(origins = "*")
public class TopologyController {

    private final TopologyAnalysisService topologyService;

    public TopologyController(TopologyAnalysisService topologyService) {
        this.topologyService = topologyService;
    }

    @GetMapping
    public ResponseEntity<ServiceTopology> getTopology() {
        List<ServiceNode> services = topologyService.generateSampleServices();
        ServiceTopology topology = topologyService.analyzeTopology(services);
        return ResponseEntity.ok(topology);
    }

    @GetMapping("/services")
    public ResponseEntity<List<ServiceNode>> getServices() {
        return ResponseEntity.ok(topologyService.generateSampleServices());
    }

    @GetMapping("/services/{serviceId}")
    public ResponseEntity<ServiceNode> getService(@PathVariable String serviceId) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        return services.stream()
                .filter(s -> s.getServiceId().equals(serviceId))
                .findFirst()
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/bottlenecks")
    public ResponseEntity<List<ServiceNode>> getBottlenecks() {
        List<ServiceNode> services = topologyService.generateSampleServices();
        ServiceTopology topology = topologyService.analyzeTopology(services);
        return ResponseEntity.ok(topologyService.identifyBottlenecks(topology));
    }
}
