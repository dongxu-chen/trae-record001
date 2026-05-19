package com.risk.engine.controller;

import com.risk.engine.dto.DecisionRequest;
import com.risk.engine.service.SimulationService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/simulation")
@Api(tags = "模拟测试")
public class SimulationController {

    @Autowired
    private SimulationService simulationService;

    @PostMapping("/replay/{requestId}")
    @ApiOperation("回放单个历史请求")
    public ResponseEntity<Map<String, Object>> replayByRequestId(@PathVariable String requestId) {
        return ResponseEntity.ok(simulationService.replayByRequestId(requestId));
    }

    @PostMapping("/replay/user/{userId}")
    @ApiOperation("回放用户所有历史请求")
    public ResponseEntity<Map<String, Object>> replayByUserId(
            @PathVariable String userId,
            @RequestParam(defaultValue = "100") int limit) {
        return ResponseEntity.ok(simulationService.replayByUserId(userId, limit));
    }

    @PostMapping("/replay/batch")
    @ApiOperation("批量回放请求")
    public ResponseEntity<Map<String, Object>> batchReplay(
            @RequestBody List<String> requestIds,
            @RequestParam(defaultValue = "10") int concurrency) {
        return ResponseEntity.ok(simulationService.batchReplay(requestIds, concurrency));
    }

    @PostMapping("/regression")
    @ApiOperation("回归测试 - 回放最近样本")
    public ResponseEntity<Map<String, Object>> regressionTest(
            @RequestParam(required = false) String scene,
            @RequestParam(defaultValue = "100") int sampleSize) {
        return ResponseEntity.ok(simulationService.regressionTest(scene, sampleSize));
    }

    @PostMapping("/scenario")
    @ApiOperation("自定义场景测试 - 批量测试不同变量组合")
    public ResponseEntity<Map<String, Object>> customScenarioTest(
            @RequestBody Map<String, Object> requestBody) {
        DecisionRequest baseRequest = new DecisionRequest();
        baseRequest.setRequestId((String) requestBody.get("requestId"));
        baseRequest.setScene((String) requestBody.get("scene"));
        baseRequest.setData((Map<String, Object>) requestBody.get("baseData"));
        
        List<Map<String, Object>> variations = (List<Map<String, Object>>) requestBody.get("variations");
        
        return ResponseEntity.ok(simulationService.customScenarioTest(baseRequest, variations));
    }
}
