package com.ratelimit.center.controller;

import com.ratelimit.center.common.Result;
import com.ratelimit.center.service.MetricService;
import com.ratelimit.center.service.MetricService.AggregatedMetric;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/metrics")
public class MetricController {

    @Autowired
    private MetricService metricService;

    @GetMapping("/resource")
    public Result<Map<String, Object>> getResourceMetrics(@RequestParam String resource) {
        Map<String, Object> metrics = metricService.getResourceMetrics(resource);
        if (metrics == null) {
            return Result.fail("No metrics found for resource: " + resource);
        }
        return Result.success(metrics);
    }

    @GetMapping("/all")
    public Result<Map<String, Map<String, Object>>> getAllResourceMetrics() {
        return Result.success(metricService.getAllResourceMetrics());
    }

    @GetMapping("/aggregated/minute")
    public Result<List<AggregatedMetric>> queryMinuteMetrics(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) String resource,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime) {
        return Result.success(metricService.queryMinuteMetrics(serviceName, resource, startTime, endTime));
    }

    @GetMapping("/aggregated/hour")
    public Result<List<AggregatedMetric>> queryHourMetrics(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) String resource,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime) {
        return Result.success(metricService.queryHourMetrics(serviceName, resource, startTime, endTime));
    }

    @GetMapping("/aggregated/stats")
    public Result<Map<String, Object>> getAggregatedStats(
            @RequestParam(required = false) String serviceName,
            @RequestParam(defaultValue = "minute") String granularity,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime) {
        return Result.success(metricService.getAggregatedStats(serviceName, granularity, startTime, endTime));
    }

    @GetMapping("/accumulator/status")
    public Result<Map<String, Object>> getAccumulatorStatus() {
        return Result.success(metricService.getCurrentAccumulatorStatus());
    }
}
