package com.risk.engine.controller;

import com.risk.engine.dto.DecisionRequest;
import com.risk.engine.dto.DecisionResponse;
import com.risk.engine.service.EasyDecisionService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/decision")
@Api(tags = "风控决策(EasyRules)")
public class EasyDecisionController {

    @Autowired
    private EasyDecisionService decisionService;

    @PostMapping
    @ApiOperation("执行风控决策")
    public ResponseEntity<DecisionResponse> makeDecision(@RequestBody DecisionRequest request) {
        return ResponseEntity.ok(decisionService.makeDecision(request));
    }

    @PostMapping("/rules/reload")
    @ApiOperation("热部署所有规则")
    public ResponseEntity<Map<String, Object>> reloadAllRules() {
        return ResponseEntity.ok(Map.of(
            "success", decisionService.reloadAllRules(),
            "status", decisionService.getEngineStatus()
        ));
    }

    @PostMapping("/rules/reload/{scene}")
    @ApiOperation("热部署指定场景的规则")
    public ResponseEntity<Map<String, Object>> reloadRulesByScene(@PathVariable String scene) {
        boolean success = decisionService.reloadRules(scene);
        return ResponseEntity.ok(Map.of(
            "success", success,
            "scene", scene,
            "version", decisionService.getRuleVersion(scene)
        ));
    }

    @GetMapping("/rules/version/{scene}")
    @ApiOperation("获取规则版本")
    public ResponseEntity<Map<String, Object>> getRuleVersion(@PathVariable String scene) {
        return ResponseEntity.ok(Map.of(
            "scene", scene,
            "version", decisionService.getRuleVersion(scene)
        ));
    }

    @GetMapping("/rules/status")
    @ApiOperation("获取规则引擎状态")
    public ResponseEntity<Map<String, Object>> getEngineStatus() {
        return ResponseEntity.ok(decisionService.getEngineStatus());
    }
}
