package com.tracking.query.controller;

import com.tracking.common.model.ClickStreamQuery;
import com.tracking.common.model.ClickStreamResult;
import com.tracking.common.model.TrackEvent;
import com.tracking.query.service.ClickStreamService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/v1/clickstream")
@Api(tags = "点击流查询")
public class ClickStreamController {

    private final ClickStreamService clickStreamService;

    public ClickStreamController(ClickStreamService clickStreamService) {
        this.clickStreamService = clickStreamService;
    }

    @PostMapping("/query")
    @ApiOperation("查询点击流数据")
    public ResponseEntity<Map<String, Object>> queryClickStream(@RequestBody ClickStreamQuery query) {
        Map<String, Object> response = new HashMap<>();
        try {
            ClickStreamResult result = clickStreamService.queryClickStream(query);
            response.put("code", 0);
            response.put("message", "success");
            response.put("data", result);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            response.put("code", 500);
            response.put("message", "查询失败: " + e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/user/{userId}")
    @ApiOperation("查询用户点击流")
    public ResponseEntity<Map<String, Object>> getUserClickStream(
            @ApiParam("用户ID") @PathVariable String userId,
            @ApiParam("开始时间戳") @RequestParam(required = false) Long startTime,
            @ApiParam("结束时间戳") @RequestParam(required = false) Long endTime,
            @ApiParam("页码") @RequestParam(defaultValue = "1") Integer page,
            @ApiParam("每页大小") @RequestParam(defaultValue = "20") Integer pageSize) {
        Map<String, Object> response = new HashMap<>();
        try {
            List<TrackEvent> events = clickStreamService.queryUserClickStream(
                    userId, startTime, endTime, page, pageSize);
            response.put("code", 0);
            response.put("message", "success");
            response.put("data", events);
            response.put("total", events.size());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            response.put("code", 500);
            response.put("message", "查询失败: " + e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/session/{sessionId}")
    @ApiOperation("查询会话点击流")
    public ResponseEntity<Map<String, Object>> getSessionClickStream(
            @ApiParam("会话ID") @PathVariable String sessionId,
            @ApiParam("页码") @RequestParam(defaultValue = "1") Integer page,
            @ApiParam("每页大小") @RequestParam(defaultValue = "100") Integer pageSize) {
        Map<String, Object> response = new HashMap<>();
        try {
            List<TrackEvent> events = clickStreamService.querySessionClickStream(sessionId, page, pageSize);
            response.put("code", 0);
            response.put("message", "success");
            response.put("data", events);
            response.put("total", events.size());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            response.put("code", 500);
            response.put("message", "查询失败: " + e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/active-users")
    @ApiOperation("统计活跃用户数")
    public ResponseEntity<Map<String, Object>> getActiveUsers(
            @ApiParam("开始时间戳") @RequestParam(required = false) Long startTime,
            @ApiParam("结束时间戳") @RequestParam(required = false) Long endTime,
            @ApiParam("平台") @RequestParam(required = false) String platform,
            @ApiParam("应用ID") @RequestParam(required = false) String appId) {
        Map<String, Object> response = new HashMap<>();
        try {
            long count = clickStreamService.countActiveUsers(startTime, endTime, platform, appId);
            response.put("code", 0);
            response.put("message", "success");
            response.put("data", count);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            response.put("code", 500);
            response.put("message", "查询失败: " + e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }
}
