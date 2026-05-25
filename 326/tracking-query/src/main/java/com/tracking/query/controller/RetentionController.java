package com.tracking.query.controller;

import com.tracking.common.model.RetentionQuery;
import com.tracking.common.model.RetentionResult;
import com.tracking.common.response.ApiResponse;
import com.tracking.storage.dao.RetentionDao;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.List;

@RestController
@RequestMapping("/api/v1/retention")
public class RetentionController {

    private final RetentionDao retentionDao;

    public RetentionController(RetentionDao retentionDao) {
        this.retentionDao = retentionDao;
    }

    @PostMapping("/analysis")
    public ApiResponse<RetentionResult> analyzeRetention(@RequestBody RetentionQuery query) {
        if (query.getInitialEvent() == null || query.getReturnEvent() == null) {
            return ApiResponse.error("initialEvent and returnEvent are required");
        }
        if (query.getStartTime() == null || query.getEndTime() == null) {
            return ApiResponse.error("startTime and endTime are required");
        }

        try {
            RetentionResult result = retentionDao.calculateRetention(query);
            return ApiResponse.success(result);
        } catch (Exception e) {
            return ApiResponse.error("Failed to analyze retention: " + e.getMessage());
        }
    }

    @GetMapping("/analysis")
    public ApiResponse<RetentionResult> analyzeRetentionByParams(
            @RequestParam String initialEvent,
            @RequestParam String returnEvent,
            @RequestParam Long startTime,
            @RequestParam Long endTime,
            @RequestParam(required = false) List<Integer> retentionDays,
            @RequestParam(required = false) String platform,
            @RequestParam(required = false) String appId,
            @RequestParam(required = false) String channel,
            @RequestParam(required = false) String groupBy,
            @RequestParam(defaultValue = "true") Boolean useCache) {

        if (retentionDays == null || retentionDays.isEmpty()) {
            retentionDays = Arrays.asList(1, 3, 7, 14, 30);
        }

        RetentionQuery query = RetentionQuery.builder()
                .initialEvent(initialEvent)
                .returnEvent(returnEvent)
                .startTime(startTime)
                .endTime(endTime)
                .retentionDays(retentionDays)
                .platform(platform)
                .appId(appId)
                .channel(channel)
                .groupBy(groupBy)
                .useCache(useCache)
                .build();

        try {
            RetentionResult result = retentionDao.calculateRetention(query);
            return ApiResponse.success(result);
        } catch (Exception e) {
            return ApiResponse.error("Failed to analyze retention: " + e.getMessage());
        }
    }

    @PostMapping("/classic")
    public ApiResponse<RetentionResult> classicRetention(
            @RequestParam Long startTime,
            @RequestParam Long endTime,
            @RequestParam(required = false) List<Integer> retentionDays,
            @RequestParam(required = false) String platform,
            @RequestParam(required = false) String appId) {

        RetentionQuery query = RetentionQuery.builder()
                .retentionType("classic")
                .initialEvent("app_install")
                .returnEvent("app_open")
                .startTime(startTime)
                .endTime(endTime)
                .retentionDays(retentionDays)
                .platform(platform)
                .appId(appId)
                .useCache(true)
                .build();

        try {
            RetentionResult result = retentionDao.calculateRetention(query);
            return ApiResponse.success(result);
        } catch (Exception e) {
            return ApiResponse.error("Failed to calculate classic retention: " + e.getMessage());
        }
    }

    @PostMapping("/custom")
    public ApiResponse<RetentionResult> customRetention(
            @RequestParam String initialEvent,
            @RequestParam String returnEvent,
            @RequestParam Long startTime,
            @RequestParam Long endTime,
            @RequestParam(required = false) List<Integer> retentionDays,
            @RequestParam(required = false) String platform,
            @RequestParam(required = false) String appId,
            @RequestParam(required = false) String channel) {

        RetentionQuery query = RetentionQuery.builder()
                .retentionType("custom")
                .initialEvent(initialEvent)
                .returnEvent(returnEvent)
                .startTime(startTime)
                .endTime(endTime)
                .retentionDays(retentionDays)
                .platform(platform)
                .appId(appId)
                .channel(channel)
                .useCache(true)
                .build();

        try {
            RetentionResult result = retentionDao.calculateRetention(query);
            return ApiResponse.success(result);
        } catch (Exception e) {
            return ApiResponse.error("Failed to calculate custom retention: " + e.getMessage());
        }
    }
}
