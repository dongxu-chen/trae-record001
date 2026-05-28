package com.ratelimit.center.controller;

import com.ratelimit.center.common.Result;
import com.ratelimit.center.service.WarmUpService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/warm-up")
public class WarmUpController {

    @Autowired
    private WarmUpService warmUpService;

    @PostMapping("/start")
    public Result<Void> startWarmUp(
            @RequestParam String resource,
            @RequestParam double targetQps,
            @RequestParam(defaultValue = "10") int warmUpSeconds,
            @RequestParam(defaultValue = "0") int curveType,
            @RequestParam(required = false) Double exponentialFactor) {
        warmUpService.startWarmUp(resource, targetQps, warmUpSeconds, curveType, exponentialFactor);
        return Result.success();
    }

    @PostMapping("/start/linear")
    public Result<Void> startLinearWarmUp(
            @RequestParam String resource,
            @RequestParam double targetQps,
            @RequestParam(defaultValue = "10") int warmUpSeconds) {
        warmUpService.startLinearWarmUp(resource, targetQps, warmUpSeconds);
        return Result.success();
    }

    @PostMapping("/start/exponential")
    public Result<Void> startExponentialWarmUp(
            @RequestParam String resource,
            @RequestParam double targetQps,
            @RequestParam(defaultValue = "10") int warmUpSeconds,
            @RequestParam(defaultValue = "3.0") double factor) {
        warmUpService.startExponentialWarmUp(resource, targetQps, warmUpSeconds, factor);
        return Result.success();
    }

    @PostMapping("/stop")
    public Result<Void> stopWarmUp(@RequestParam String resource) {
        warmUpService.stopWarmUp(resource);
        return Result.success();
    }

    @GetMapping("/status")
    public Result<Map<String, Object>> getWarmUpStatus(@RequestParam String resource) {
        Map<String, Object> status = warmUpService.getWarmUpStatus(resource);
        if (status == null) {
            return Result.fail("Warm-up not found for resource: " + resource);
        }
        return Result.success(status);
    }

    @GetMapping("/status/all")
    public Result<List<Map<String, Object>>> getAllWarmUpStatus() {
        return Result.success(warmUpService.getAllWarmUpStatus());
    }

    @GetMapping("/current-limit")
    public Result<Double> getCurrentWarmUpLimit(@RequestParam String resource) {
        return Result.success(warmUpService.getCurrentWarmUpLimit(resource));
    }

    @GetMapping("/completed")
    public Result<Boolean> isWarmUpCompleted(@RequestParam String resource) {
        return Result.success(warmUpService.isWarmUpCompleted(resource));
    }

    @GetMapping("/chart")
    public Result<List<Map<String, Object>>> getWarmUpCurveChart(
            @RequestParam String resource,
            @RequestParam(defaultValue = "20") int points) {
        return Result.success(warmUpService.getWarmUpCurveChart(resource, points));
    }
}
