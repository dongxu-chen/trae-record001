package com.ratelimit.recommender.controller;

import com.ratelimit.recommender.model.*;
import com.ratelimit.recommender.service.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping("/ratelimit")
@CrossOrigin(origins = "*")
public class RateLimitController {

    private final QueueingTheoryService queueingService;
    private final TimeSeriesPredictionService predictionService;
    private final TopologyAnalysisService topologyService;
    private final RateLimitConfigService configService;

    public RateLimitController(QueueingTheoryService queueingService,
                               TimeSeriesPredictionService predictionService,
                               TopologyAnalysisService topologyService,
                               RateLimitConfigService configService) {
        this.queueingService = queueingService;
        this.predictionService = predictionService;
        this.topologyService = topologyService;
        this.configService = configService;
    }

    @GetMapping("/recommend/{serviceId}")
    public ResponseEntity<RateLimitRecommendation> getRecommendation(@PathVariable String serviceId) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        return services.stream()
                .filter(s -> s.getServiceId().equals(serviceId))
                .findFirst()
                .map(service -> {
                    RateLimitRecommendation recommendation = queueingService.recommendServiceRateLimit(service);
                    TrafficPrediction prediction = predictionService.predictTraffic(serviceId, 60);
                    recommendation.setPrediction(prediction);
                    return ResponseEntity.ok(recommendation);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/recommend/all")
    public ResponseEntity<List<RateLimitRecommendation>> getAllRecommendations() {
        List<ServiceNode> services = topologyService.generateSampleServices();
        List<RateLimitRecommendation> recommendations = new ArrayList<>();

        for (ServiceNode service : services) {
            RateLimitRecommendation recommendation = queueingService.recommendServiceRateLimit(service);
            recommendations.add(recommendation);
        }

        return ResponseEntity.ok(recommendations);
    }

    @PostMapping("/apply")
    public ResponseEntity<RateLimitConfig> applyRecommendation(@RequestBody RateLimitRecommendation recommendation) {
        RateLimitConfig config = configService.applyRecommendation(recommendation);
        return ResponseEntity.ok(config);
    }

    @GetMapping("/config/{serviceId}")
    public ResponseEntity<RateLimitConfig> getConfig(@PathVariable String serviceId) {
        RateLimitConfig config = configService.getConfig(serviceId);
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    @GetMapping("/configs")
    public ResponseEntity<?> getAllConfigs() {
        return ResponseEntity.ok(configService.getAllConfigs());
    }

    @PutMapping("/config/{serviceId}")
    public ResponseEntity<RateLimitConfig> updateConfig(@PathVariable String serviceId,
                                                         @RequestBody RateLimitConfig config) {
        return ResponseEntity.ok(configService.updateConfig(serviceId, config));
    }

    @DeleteMapping("/config/{serviceId}")
    public ResponseEntity<Void> deleteConfig(@PathVariable String serviceId) {
        boolean deleted = configService.deleteConfig(serviceId);
        return deleted ? ResponseEntity.ok().build() : ResponseEntity.notFound().build();
    }

    @PostMapping("/config/{serviceId}/toggle")
    public ResponseEntity<RateLimitConfig> toggleConfig(@PathVariable String serviceId,
                                                         @RequestParam boolean enabled) {
        RateLimitConfig config = configService.toggleConfig(serviceId, enabled);
        if (config == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(config);
    }

    @GetMapping("/config/{serviceId}/export")
    public ResponseEntity<String> exportConfig(@PathVariable String serviceId) {
        String yaml = configService.exportConfigAsYaml(serviceId);
        return ResponseEntity.ok(yaml);
    }
}
