package com.dlq.platform.api.controller;

import com.dlq.platform.api.common.Result;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.service.DeadLetterAnalyticsService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/analytics")
@RequiredArgsConstructor
public class AnalyticsController {

    private final DeadLetterAnalyticsService analyticsService;

    @GetMapping("/prediction/trend")
    public Result<Map<String, Object>> predictTrend(
            @RequestParam(required = false) String topic,
            @RequestParam(required = false) MqTypeEnum mqType,
            @RequestParam(defaultValue = "7") int forecastDays,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime) {

        Map<String, Object> result = analyticsService.predictDeadLetterTrend(
                topic, mqType, forecastDays, startTime, endTime);
        return Result.success(result);
    }

    @PostMapping("/auto-repair/{id}")
    public Result<Map<String, Object>> autoRepair(
            @PathVariable String id,
            @RequestParam(defaultValue = "false") boolean autoReplay) {

        Map<String, Object> result = analyticsService.tryAutoRepairAndReplay(id, autoReplay);
        return Result.success(result);
    }

    @PostMapping("/auto-repair/batch")
    public Result<Map<String, Object>> batchAutoRepair(
            @RequestBody List<String> ids,
            @RequestParam(defaultValue = "false") boolean autoReplay) {

        Map<String, Object> result = analyticsService.batchAutoRepair(ids, autoReplay);
        return Result.success(result);
    }

    @GetMapping("/auto-repair/capabilities")
    public Result<Map<String, Object>> getRepairCapabilities() {
        Map<String, Object> capabilities = analyticsService.getRepairCapabilities();
        return Result.success(capabilities);
    }

    @GetMapping("/visualization")
    public Result<Map<String, Object>> getVisualization(
            @RequestParam(defaultValue = "all") String type,
            @RequestParam(required = false) String topic,
            @RequestParam(required = false) MqTypeEnum mqType,
            @RequestParam(defaultValue = "hourly") String interval,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime) {

        Map<String, Object> result = analyticsService.getVisualizationData(
                type, topic, mqType, interval, startTime, endTime);
        return Result.success(result);
    }

    @GetMapping("/visualization/options")
    public Result<Map<String, Object>> getVisualizationOptions() {
        Map<String, Object> options = analyticsService.getVisualizationOptions();
        return Result.success(options);
    }

    @GetMapping("/visualization/timeline")
    public Result<Map<String, Object>> getTimeline(
            @RequestParam(required = false) String topic,
            @RequestParam(required = false) MqTypeEnum mqType,
            @RequestParam(defaultValue = "hourly") String interval,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime) {

        Map<String, Object> result = analyticsService.getVisualizationData(
                "timeline", topic, mqType, interval, startTime, endTime);
        return Result.success(result);
    }

    @GetMapping("/visualization/heatmap")
    public Result<Map<String, Object>> getHeatmap(
            @RequestParam(required = false) String topic,
            @RequestParam(required = false) MqTypeEnum mqType,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime) {

        Map<String, Object> result = analyticsService.getVisualizationData(
                "heatmap", topic, mqType, "hourly", startTime, endTime);
        return Result.success(result);
    }

    @GetMapping("/visualization/sankey")
    public Result<Map<String, Object>> getSankey(
            @RequestParam(required = false) String topic,
            @RequestParam(required = false) MqTypeEnum mqType,
            @RequestParam(required = false) LocalDateTime startTime,
            @RequestParam(required = false) LocalDateTime endTime) {

        Map<String, Object> result = analyticsService.getVisualizationData(
                "sankey", topic, mqType, "hourly", startTime, endTime);
        return Result.success(result);
    }
}
