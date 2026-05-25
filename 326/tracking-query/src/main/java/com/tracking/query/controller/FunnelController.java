package com.tracking.query.controller;

import com.tracking.common.model.FunnelQuery;
import com.tracking.common.model.FunnelResult;
import com.tracking.query.service.FunnelAnalysisService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/v1/funnel")
@Api(tags = "漏斗分析")
public class FunnelController {

    private final FunnelAnalysisService funnelAnalysisService;

    public FunnelController(FunnelAnalysisService funnelAnalysisService) {
        this.funnelAnalysisService = funnelAnalysisService;
    }

    @PostMapping("/analysis")
    @ApiOperation("自定义漏斗分析")
    public ResponseEntity<Map<String, Object>> analyzeFunnel(@RequestBody FunnelQuery query) {
        Map<String, Object> response = new HashMap<>();
        try {
            FunnelResult result = funnelAnalysisService.calculateFunnel(query);
            response.put("code", 0);
            response.put("message", "success");
            response.put("data", result);
            return ResponseEntity.ok(response);
        } catch (IllegalArgumentException e) {
            response.put("code", 400);
            response.put("message", e.getMessage());
            return ResponseEntity.badRequest().body(response);
        } catch (Exception e) {
            response.put("code", 500);
            response.put("message", "分析失败: " + e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/purchase")
    @ApiOperation("购买转化漏斗分析")
    public ResponseEntity<Map<String, Object>> purchaseFunnel(
            @ApiParam("开始时间戳") @RequestParam Long startTime,
            @ApiParam("结束时间戳") @RequestParam Long endTime,
            @ApiParam("平台") @RequestParam(required = false) String platform,
            @ApiParam("应用ID") @RequestParam(required = false) String appId) {
        Map<String, Object> response = new HashMap<>();
        try {
            FunnelResult result = funnelAnalysisService.calculatePurchaseFunnel(
                    startTime, endTime, platform, appId);
            response.put("code", 0);
            response.put("message", "success");
            response.put("data", result);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            response.put("code", 500);
            response.put("message", "分析失败: " + e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }

    @GetMapping("/registration")
    @ApiOperation("注册转化漏斗分析")
    public ResponseEntity<Map<String, Object>> registrationFunnel(
            @ApiParam("开始时间戳") @RequestParam Long startTime,
            @ApiParam("结束时间戳") @RequestParam Long endTime,
            @ApiParam("平台") @RequestParam(required = false) String platform,
            @ApiParam("应用ID") @RequestParam(required = false) String appId) {
        Map<String, Object> response = new HashMap<>();
        try {
            FunnelResult result = funnelAnalysisService.calculateRegistrationFunnel(
                    startTime, endTime, platform, appId);
            response.put("code", 0);
            response.put("message", "success");
            response.put("data", result);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            response.put("code", 500);
            response.put("message", "分析失败: " + e.getMessage());
            return ResponseEntity.status(500).body(response);
        }
    }
}
