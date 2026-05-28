package com.ratelimit.center.controller;

import com.ratelimit.center.common.Result;
import com.ratelimit.center.service.AdaptiveRateLimitService;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/adaptive")
public class AdaptiveRateLimitController {

    @Autowired
    private AdaptiveRateLimitService adaptiveRateLimitService;

    @GetMapping("/system-load")
    public Result<AdaptiveRateLimitService.SystemLoad> getSystemLoad() {
        return Result.success(adaptiveRateLimitService.getCurrentSystemLoad());
    }

    @PostMapping("/rule")
    public Result<Void> registerRule(@RequestBody RegisterRuleRequest request) {
        adaptiveRateLimitService.registerAdaptiveRule(
                request.getResource(),
                request.getBaseThreshold(),
                request.getStrategy()
        );
        return Result.success();
    }

    @DeleteMapping("/rule/{resource}")
    public Result<Void> unregisterRule(@PathVariable String resource) {
        adaptiveRateLimitService.unregisterAdaptiveRule(resource);
        return Result.success();
    }

    @GetMapping("/status")
    public Result<Map<String, Object>> getAdaptiveStatus() {
        return Result.success(adaptiveRateLimitService.getAdaptiveStatus());
    }

    @GetMapping("/history/{resource}")
    public Result<List<AdaptiveRateLimitService.AdjustHistory>> getAdjustHistory(
            @PathVariable String resource,
            @RequestParam(defaultValue = "100") int limit) {
        return Result.success(adaptiveRateLimitService.getAdjustHistory(resource, limit));
    }

    @PostMapping("/adjust")
    public Result<Void> triggerAdjust() {
        adaptiveRateLimitService.adjustThresholds();
        return Result.success();
    }

    @Data
    public static class RegisterRuleRequest {
        private String resource;
        private double baseThreshold;
        private String strategy = "auto";
    }
}
