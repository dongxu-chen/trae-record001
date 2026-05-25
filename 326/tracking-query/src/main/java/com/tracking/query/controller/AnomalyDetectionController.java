package com.tracking.query.controller;

import com.tracking.common.model.AnomalyAlert;
import com.tracking.common.model.AnomalyDetectionQuery;
import com.tracking.common.response.ApiResponse;
import com.tracking.storage.dao.AnomalyDetectionDao;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/anomaly")
public class AnomalyDetectionController {

    private final AnomalyDetectionDao anomalyDetectionDao;

    public AnomalyDetectionController(AnomalyDetectionDao anomalyDetectionDao) {
        this.anomalyDetectionDao = anomalyDetectionDao;
    }

    @PostMapping("/alerts/query")
    public ApiResponse<List<AnomalyAlert>> queryAlerts(@RequestBody AnomalyDetectionQuery query) {
        try {
            List<AnomalyAlert> alerts = anomalyDetectionDao.queryAlerts(query);
            return ApiResponse.success(alerts);
        } catch (Exception e) {
            return ApiResponse.error("Failed to query alerts: " + e.getMessage());
        }
    }

    @GetMapping("/alerts")
    public ApiResponse<List<AnomalyAlert>> getRecentAlerts(
            @RequestParam(required = false) String severity,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer pageSize) {

        AnomalyDetectionQuery query = AnomalyDetectionQuery.builder()
                .startTime(System.currentTimeMillis() - 24 * 3600 * 1000L)
                .endTime(System.currentTimeMillis())
                .severity(severity)
                .page(page)
                .pageSize(pageSize)
                .build();

        try {
            List<AnomalyAlert> alerts = anomalyDetectionDao.queryAlerts(query);
            return ApiResponse.success(alerts);
        } catch (Exception e) {
            return ApiResponse.error("Failed to get alerts: " + e.getMessage());
        }
    }

    @GetMapping("/stats")
    public ApiResponse<Map<String, Object>> getAlertStats(
            @RequestParam(required = false) Long startTime,
            @RequestParam(required = false) Long endTime) {

        long start = startTime != null ? startTime : System.currentTimeMillis() - 24 * 3600 * 1000L;
        long end = endTime != null ? endTime : System.currentTimeMillis();

        try {
            Map<String, Object> stats = anomalyDetectionDao.getAlertStats(start, end);
            return ApiResponse.success(stats);
        } catch (Exception e) {
            Map<String, Object> fallback = new HashMap<>();
            fallback.put("error", e.getMessage());
            return ApiResponse.success(fallback);
        }
    }

    @PostMapping("/alert/{alertId}/acknowledge")
    public ApiResponse<String> acknowledgeAlert(
            @PathVariable String alertId,
            @RequestParam String acknowledgedBy,
            @RequestParam(required = false) String comment) {

        try {
            boolean result = anomalyDetectionDao.acknowledgeAlert(alertId, acknowledgedBy, comment);
            if (result) {
                return ApiResponse.success("Alert acknowledged successfully");
            } else {
                return ApiResponse.error("Failed to acknowledge alert");
            }
        } catch (Exception e) {
            return ApiResponse.error("Error: " + e.getMessage());
        }
    }
}
