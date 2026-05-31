package com.flink.recommender.controller;

import com.flink.recommender.cost.CostEstimationService;
import com.flink.recommender.model.ResourceConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/cost")
@CrossOrigin(origins = "http://localhost:3000")
public class CostController {

    private static final Logger logger = LoggerFactory.getLogger(CostController.class);

    private final CostEstimationService costEstimationService;

    public CostController(CostEstimationService costEstimationService) {
        this.costEstimationService = costEstimationService;
    }

    @PostMapping("/calculate")
    public ResponseEntity<?> calculateCost(@RequestBody ResourceConfig config) {
        logger.info("Calculating cost for configuration");
        Map<String, Object> cost = costEstimationService.calculateJobCost(config);
        return ResponseEntity.ok(cost);
    }

    @PostMapping("/compare")
    public ResponseEntity<?> compareCosts(
            @RequestBody Map<String, ResourceConfig> configs) {
        logger.info("Comparing costs between configurations");

        ResourceConfig current = configs.get("current");
        ResourceConfig proposed = configs.get("proposed");

        if (current == null || proposed == null) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "Both 'current' and 'proposed' configurations are required"));
        }

        Map<String, Object> comparison = costEstimationService.compareCosts(current, proposed);
        return ResponseEntity.ok(comparison);
    }

    @PostMapping("/tco")
    public ResponseEntity<?> calculateTco(
            @RequestBody ResourceConfig config,
            @RequestParam(defaultValue = "12") int months) {
        logger.info("Calculating TCO for {} months", months);
        Map<String, Object> tco = costEstimationService.calculateTotalCostOfOwnership(config, months);
        return ResponseEntity.ok(tco);
    }

    @PostMapping("/simulate-scaling")
    public ResponseEntity<?> simulateScaling(
            @RequestBody ResourceConfig baseConfig,
            @RequestParam int[] factors) {
        logger.info("Simulating scaling with factors: {}", factors);
        Map<String, Object> simulations = costEstimationService.simulateScalingCosts(baseConfig, factors);
        return ResponseEntity.ok(simulations);
    }

    @GetMapping("/simulator")
    public ResponseEntity<?> getCostSimulatorData() {
        logger.info("Getting cost simulator data");

        ResourceConfig baseConfig = ResourceConfig.builder()
                .jobId("simulator")
                .jobName("Cost Simulator")
                .jobManagerMemoryMb(1024)
                .taskManagerMemoryMb(4096)
                .taskManagerCpuCores(1.0)
                .numTaskManagers(4)
                .parallelism(4)
                .build();

        int[] factors = {50, 75, 100, 125, 150, 200};
        Map<String, Object> simulations = costEstimationService.simulateScalingCosts(baseConfig, factors);

        return ResponseEntity.ok(Map.of(
                "baseConfig", baseConfig,
                "simulations", simulations
        ));
    }

    @GetMapping("/network-report/{jobId}")
    public ResponseEntity<?> getNetworkCostReport(@PathVariable String jobId) {
        logger.info("Getting network cost report for job: {}", jobId);

        ResourceConfig config = ResourceConfig.builder()
                .jobId(jobId)
                .jobName("Network Cost Analysis")
                .jobManagerMemoryMb(1024)
                .taskManagerMemoryMb(4096)
                .taskManagerCpuCores(1.0)
                .numTaskManagers(8)
                .parallelism(8)
                .build();

        Map<String, Object> report = costEstimationService.getNetworkCostReport(config);
        return ResponseEntity.ok(report);
    }

    @GetMapping("/network-report")
    public ResponseEntity<?> getNetworkCostReport() {
        return getNetworkCostReport("demo-job");
    }
}
