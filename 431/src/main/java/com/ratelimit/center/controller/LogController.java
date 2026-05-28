package com.ratelimit.center.controller;

import com.ratelimit.center.common.PageResult;
import com.ratelimit.center.common.Result;
import com.ratelimit.center.entity.RateLimitLogEntity;
import com.ratelimit.center.service.RateLimitLogService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/logs")
public class LogController {

    @Autowired
    private RateLimitLogService rateLimitLogService;

    @GetMapping
    public Result<PageResult<RateLimitLogEntity>> queryLogs(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) String resource,
            @RequestParam(required = false) String ruleType,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "20") Integer size) {
        return Result.success(rateLimitLogService.queryLogs(
                serviceName, resource, ruleType, startTime, endTime, page, size
        ));
    }

    @GetMapping("/stats")
    public Result<Map<String, Object>> getLogStats(
            @RequestParam(required = false) String serviceName,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime) {
        return Result.success(rateLimitLogService.getLogStats(serviceName, startTime, endTime));
    }
}
