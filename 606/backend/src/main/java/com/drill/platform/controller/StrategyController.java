package com.drill.platform.controller;

import com.drill.platform.model.ApiResult;
import com.drill.platform.model.RateLimitStrategy;
import com.drill.platform.service.DrillService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/strategy")
public class StrategyController {

    private final DrillService drillService;

    public StrategyController(DrillService drillService) {
        this.drillService = drillService;
    }

    @PostMapping
    public ApiResult<RateLimitStrategy> createStrategy(@RequestBody RateLimitStrategy strategy) {
        return ApiResult.success(drillService.createStrategy(strategy));
    }

    @PutMapping("/{strategyId}")
    public ApiResult<RateLimitStrategy> updateStrategy(
            @PathVariable String strategyId,
            @RequestBody RateLimitStrategy strategy) {
        return ApiResult.success(drillService.updateStrategy(strategyId, strategy));
    }

    @DeleteMapping("/{strategyId}")
    public ApiResult<Void> deleteStrategy(@PathVariable String strategyId) {
        drillService.deleteStrategy(strategyId);
        return ApiResult.success(null);
    }

    @GetMapping
    public ApiResult<List<RateLimitStrategy>> listStrategies() {
        return ApiResult.success(drillService.listStrategies());
    }

    @GetMapping("/{strategyId}")
    public ApiResult<RateLimitStrategy> getStrategy(@PathVariable String strategyId) {
        RateLimitStrategy strategy = drillService.getStrategy(strategyId);
        if (strategy == null) {
            return ApiResult.error(404, "Strategy not found");
        }
        return ApiResult.success(strategy);
    }
}
