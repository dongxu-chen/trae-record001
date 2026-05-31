package com.drill.platform.controller;

import com.drill.platform.model.*;
import com.drill.platform.recommendation.StrategyRecommendationEngine;
import com.drill.platform.service.DrillService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/recommendation")
public class RecommendationController {

    private final StrategyRecommendationEngine recommendationEngine;
    private final DrillService drillService;

    public RecommendationController(
            StrategyRecommendationEngine recommendationEngine,
            DrillService drillService) {
        this.recommendationEngine = recommendationEngine;
        this.drillService = drillService;
    }

    @GetMapping("/strategy")
    public ApiResult<StrategyRecommendation> getStrategyRecommendation(
            @RequestParam(required = false, defaultValue = "default") String targetSystem,
            @RequestParam(required = false, defaultValue = "true") boolean includeAlternatives) {
        
        List<RateLimitStrategy> strategies = List.of(
                createStrategy("1", "默认限流策略", "QPS_THRESHOLD", 100, 5000),
                createStrategy("2", "保守策略", "QPS_THRESHOLD", 50, 3000),
                createStrategy("3", "激进策略", "QPS_THRESHOLD", 200, 10000),
                createStrategy("4", "线程隔离策略", "THREAD_COUNT", 50, 5000),
                createStrategy("5", "混合策略", "QPS_THRESHOLD", 150, 8000)
        );
        
        List<DrillTask> historicalDrills = drillService.listTasks();
        
        StrategyRecommendation recommendation = recommendationEngine.generateRecommendation(
                targetSystem, strategies, historicalDrills);
        
        if (!includeAlternatives) {
            recommendation.setAlternativeStrategies(null);
        }
        
        return ApiResult.success(recommendation);
    }

    @PostMapping("/strategy/verify")
    public ApiResult<StrategyRecommendation> verifyRecommendation(
            @RequestBody StrategyRecommendation recommendation) {
        return ApiResult.success(recommendation);
    }

    @GetMapping("/strategy/variants")
    public ApiResult<List<RateLimitStrategy>> generateStrategyVariants(
            @RequestParam String strategyId,
            @RequestParam(required = false, defaultValue = "5") int count) {
        
        RateLimitStrategy base = new RateLimitStrategy();
        base.setId(strategyId);
        base.setName("基准策略");
        base.setType("QPS_THRESHOLD");
        base.setThreshold(100);
        base.setTimeoutMs(5000);
        
        List<RateLimitStrategy> variants = recommendationEngine.generateStrategyVariants(base);
        
        return ApiResult.success(variants.subList(0, Math.min(count, variants.size())));
    }

    private RateLimitStrategy createStrategy(
            String id, String name, String type, int threshold, int timeoutMs) {
        RateLimitStrategy strategy = new RateLimitStrategy();
        strategy.setId(id);
        strategy.setName(name);
        strategy.setType(type);
        strategy.setThreshold(threshold);
        strategy.setTimeoutMs(timeoutMs);
        strategy.setDescription(name + "描述");
        return strategy;
    }
}
