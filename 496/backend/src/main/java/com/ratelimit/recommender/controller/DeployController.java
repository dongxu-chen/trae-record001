package com.ratelimit.recommender.controller;

import com.ratelimit.recommender.model.*;
import com.ratelimit.recommender.service.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/deploy")
@CrossOrigin(origins = "*")
public class DeployController {

    private final AutoDeployService deployService;
    private final TopologyAnalysisService topologyService;
    private final QueueingTheoryService queueingService;

    public DeployController(AutoDeployService deployService,
                             TopologyAnalysisService topologyService,
                             QueueingTheoryService queueingService) {
        this.deployService = deployService;
        this.topologyService = topologyService;
        this.queueingService = queueingService;
    }

    @PostMapping("/gateway/{gatewayId}")
    public ResponseEntity<AutoDeployResult> deployToGateway(
            @PathVariable String gatewayId,
            @RequestParam(defaultValue = "true") boolean autoApprove) {
        return ResponseEntity.ok(deployService.deployToGateway(gatewayId, autoApprove));
    }

    @PostMapping("/service/{serviceId}")
    public ResponseEntity<AutoDeployResult> deployService(
            @PathVariable String serviceId) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        return services.stream()
                .filter(s -> s.getServiceId().equals(serviceId))
                .findFirst()
                .map(service -> {
                    RateLimitRecommendation rec = queueingService.recommendServiceRateLimit(service);
                    return ResponseEntity.ok(deployService.deploySingleService(serviceId, rec));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/rollback/{deployId}")
    public ResponseEntity<AutoDeployResult> rollback(@PathVariable String deployId) {
        AutoDeployResult result = deployService.rollback(deployId);
        if (result == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/history")
    public ResponseEntity<List<AutoDeployResult>> getDeployHistory() {
        return ResponseEntity.ok(deployService.getDeployHistory());
    }

    @GetMapping("/result/{deployId}")
    public ResponseEntity<AutoDeployResult> getDeployResult(@PathVariable String deployId) {
        AutoDeployResult result = deployService.getDeployResult(deployId);
        if (result == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(result);
    }
}
