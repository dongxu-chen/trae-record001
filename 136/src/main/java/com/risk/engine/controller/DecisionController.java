package com.risk.engine.controller;

import com.risk.engine.dto.DecisionRequest;
import com.risk.engine.dto.DecisionResponse;
import com.risk.engine.service.DecisionService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/decision")
@Api(tags = "风控决策")
public class DecisionController {

    @Autowired
    private DecisionService decisionService;

    @PostMapping
    @ApiOperation("实时风控决策")
    public ResponseEntity<DecisionResponse> makeDecision(@RequestBody DecisionRequest request) {
        return ResponseEntity.ok(decisionService.makeDecision(request));
    }

    @PostMapping("/rules/reload")
    @ApiOperation("热重载规则")
    public ResponseEntity<String> reloadRules(@RequestParam String scene,
                                              @RequestBody String rulesContent) {
        boolean success = decisionService.reloadRules(scene, rulesContent);
        if (success) {
            return ResponseEntity.ok("规则重载成功");
        } else {
            return ResponseEntity.badRequest().body("规则重载失败，请检查规则语法");
        }
    }

    @GetMapping("/rules/version")
    @ApiOperation("获取规则版本")
    public ResponseEntity<Long> getRuleVersion(@RequestParam String scene) {
        return ResponseEntity.ok(decisionService.getRuleVersion(scene));
    }
}
