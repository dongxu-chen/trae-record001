package com.ratelimit.recommender.controller;

import com.ratelimit.recommender.model.*;
import com.ratelimit.recommender.service.OverloadSimulationService;
import com.ratelimit.recommender.service.TopologyAnalysisService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/simulation")
@CrossOrigin(origins = "*")
public class SimulationController {

    private final OverloadSimulationService simulationService;
    private final TopologyAnalysisService topologyService;

    public SimulationController(OverloadSimulationService simulationService,
                                 TopologyAnalysisService topologyService) {
        this.simulationService = simulationService;
        this.topologyService = topologyService;
    }

    @PostMapping("/overload/{serviceId}")
    public ResponseEntity<OverloadSimulationResult> runSimulation(
            @PathVariable String serviceId,
            @RequestBody OverloadSimulationRequest request) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        return services.stream()
                .filter(s -> s.getServiceId().equals(serviceId))
                .findFirst()
                .map(service -> ResponseEntity.ok(
                        simulationService.runSimulation(service, request, false)))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/overload/{serviceId}/protected")
    public ResponseEntity<OverloadSimulationResult> runProtectedSimulation(
            @PathVariable String serviceId,
            @RequestBody OverloadSimulationRequest request) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        return services.stream()
                .filter(s -> s.getServiceId().equals(serviceId))
                .findFirst()
                .map(service -> ResponseEntity.ok(
                        simulationService.runSimulation(service, request, true)))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/overload/{serviceId}/compare")
    public ResponseEntity<List<OverloadSimulationResult>> compareSimulation(
            @PathVariable String serviceId,
            @RequestBody OverloadSimulationRequest request) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        return services.stream()
                .filter(s -> s.getServiceId().equals(serviceId))
                .findFirst()
                .map(service -> ResponseEntity.ok(
                        simulationService.compareSimulation(service, request)))
                .orElse(ResponseEntity.notFound().build());
    }
}
