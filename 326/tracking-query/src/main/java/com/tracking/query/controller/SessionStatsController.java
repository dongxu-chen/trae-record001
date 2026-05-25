package com.tracking.query.controller;

import com.tracking.common.model.UserSessionStats;
import com.tracking.storage.dao.UserSessionStatsDao;
import com.tracking.common.util.SessionIntervalAnalyzer;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Api(tags = "会话统计管理")
@RestController
@RequestMapping("/api/v1/session-stats")
public class SessionStatsController {

    private final UserSessionStatsDao userSessionStatsDao;

    public SessionStatsController(UserSessionStatsDao userSessionStatsDao) {
        this.userSessionStatsDao = userSessionStatsDao;
    }

    @ApiOperation("获取用户的会话统计信息")
    @GetMapping("/user/{userId}")
    public ResponseEntity<Map<String, Object>> getUserSessionStats(
            @ApiParam("用户ID") @PathVariable String userId) {
        UserSessionStats stats = userSessionStatsDao.getUserSessionStats(userId, null);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", stats);
        
        if (stats != null) {
            result.put("dynamicTimeoutMinutes", stats.getDynamicSessionTimeout() / 60000);
            result.put("isDynamic", stats.getSampleSize() >= 10);
        }
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("获取用户的动态会话超时时间")
    @GetMapping("/timeout/{userId}")
    public ResponseEntity<Map<String, Object>> getDynamicTimeout(
            @ApiParam("用户ID") @PathVariable String userId) {
        Long timeout = userSessionStatsDao.getDynamicSessionTimeout(userId, null);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("userId", userId);
        result.put("dynamicTimeoutMs", timeout);
        result.put("dynamicTimeoutMinutes", timeout / 60000);
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("分析会话间隔并计算动态阈值")
    @PostMapping("/analyze")
    public ResponseEntity<Map<String, Object>> analyzeSessionIntervals(
            @ApiParam("用户ID") @RequestParam(required = false) String userId,
            @ApiParam("匿名ID") @RequestParam(required = false) String anonymousId,
            @ApiParam("平台") @RequestParam(required = false) String platform,
            @ApiParam("应用ID") @RequestParam(required = false) String appId,
            @RequestBody List<Long> sessionEndTimes) {
        
        UserSessionStats stats = SessionIntervalAnalyzer.analyzeSessionIntervals(
            sessionEndTimes, userId, anonymousId, platform, appId);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("data", stats);
        result.put("dynamicTimeoutMinutes", stats.getDynamicSessionTimeout() / 60000);
        result.put("sampleSize", stats.getSampleSize());
        result.put("hasEnoughSamples", stats.getSampleSize() >= 10);
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("计算动态会话超时时间")
    @PostMapping("/calculate-timeout")
    public ResponseEntity<Map<String, Object>> calculateDynamicTimeout(
            @ApiParam("平均间隔(ms)") @RequestParam long avg,
            @ApiParam("中位数间隔(ms)") @RequestParam long median,
            @ApiParam("P75间隔(ms)") @RequestParam long p75,
            @ApiParam("P90间隔(ms)") @RequestParam long p90,
            @ApiParam("样本数量") @RequestParam(defaultValue = "50") int sampleSize) {
        
        long timeout = SessionIntervalAnalyzer.calculateDynamicSessionTimeout(avg, median, p75, p90, sampleSize);
        
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("dynamicTimeoutMs", timeout);
        result.put("dynamicTimeoutMinutes", timeout / 60000);
        result.put("input", Map.of(
            "avg", avg,
            "median", median,
            "p75", p75,
            "p90", p90,
            "sampleSize", sampleSize
        ));
        
        return ResponseEntity.ok(result);
    }

    @ApiOperation("计算百分位数值")
    @PostMapping("/percentile")
    public ResponseEntity<Map<String, Object>> calculatePercentile(
            @RequestBody List<Long> values,
            @ApiParam("百分位") @RequestParam(defaultValue = "90") double percentile) {
        
        values.sort(Long::compareTo);
        long result = SessionIntervalAnalyzer.calculatePercentile(values, percentile);
        
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("percentile", percentile);
        response.put("value", result);
        response.put("sortedValues", values);
        response.put("count", values.size());
        
        return ResponseEntity.ok(response);
    }
}
