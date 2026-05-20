package com.risk.engine.controller;

import com.risk.engine.entity.DecisionTrace;
import com.risk.engine.service.DecisionTraceService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/traces")
@Api(tags = "决策轨迹")
public class TraceController {

    @Autowired
    private DecisionTraceService traceService;

    @GetMapping("/{requestId}")
    @ApiOperation("获取请求的完整决策轨迹")
    public ResponseEntity<Map<String, Object>> getTraceDetail(@PathVariable String requestId) {
        return ResponseEntity.ok(traceService.getTraceDetail(requestId));
    }

    @GetMapping("/user/{userId}")
    @ApiOperation("查询用户的决策轨迹")
    public ResponseEntity<List<DecisionTrace>> getUserTraces(
            @PathVariable String userId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime) {
        return ResponseEntity.ok(traceService.getUserTraces(userId, startTime, endTime));
    }

    @GetMapping("/step/{step}")
    @ApiOperation("按步骤查询决策轨迹")
    public ResponseEntity<List<DecisionTrace>> getStepTraces(
            @PathVariable String step,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime) {
        return ResponseEntity.ok(traceService.getStepTraces(step, startTime, endTime));
    }

    @GetMapping("/result/{result}")
    @ApiOperation("按结果查询请求ID")
    public ResponseEntity<List<String>> findRequestIdsByResult(
            @PathVariable String result,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endTime) {
        return ResponseEntity.ok(traceService.findRequestIdsByResult(result, startTime, endTime));
    }
}
