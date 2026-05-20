package com.risk.engine.controller;

import com.risk.engine.entity.Rule;
import com.risk.engine.service.RuleService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/rules")
@Api(tags = "规则管理")
public class RuleController {

    @Autowired
    private RuleService ruleService;

    @PostMapping
    @ApiOperation("创建规则")
    public ResponseEntity<Rule> createRule(@RequestBody Rule rule) {
        return ResponseEntity.ok(ruleService.createRule(rule));
    }

    @GetMapping("/{id}")
    @ApiOperation("根据ID查询规则")
    public ResponseEntity<Rule> getRuleById(@PathVariable Long id) {
        return ruleService.getRuleById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/code/{ruleCode}")
    @ApiOperation("根据编码查询规则")
    public ResponseEntity<Rule> getRuleByCode(@PathVariable String ruleCode) {
        return ruleService.getRuleByCode(ruleCode)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    @ApiOperation("查询所有规则")
    public ResponseEntity<List<Rule>> getAllRules() {
        return ResponseEntity.ok(ruleService.getAllRules());
    }

    @GetMapping("/enabled")
    @ApiOperation("查询所有启用的规则")
    public ResponseEntity<List<Rule>> getEnabledRules() {
        return ResponseEntity.ok(ruleService.getEnabledRules());
    }

    @GetMapping("/enabled/scene/{scene}")
    @ApiOperation("根据场景查询启用的规则")
    public ResponseEntity<List<Rule>> getEnabledRulesByScene(@PathVariable String scene) {
        return ResponseEntity.ok(ruleService.getEnabledRulesByScene(scene));
    }

    @PutMapping("/{id}")
    @ApiOperation("更新规则")
    public ResponseEntity<Rule> updateRule(@PathVariable Long id, @RequestBody Rule rule) {
        return ResponseEntity.ok(ruleService.updateRule(id, rule));
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除规则")
    public ResponseEntity<Void> deleteRule(@PathVariable Long id) {
        ruleService.deleteRule(id);
        return ResponseEntity.ok().build();
    }

    @PatchMapping("/{id}/status")
    @ApiOperation("更新规则状态")
    public ResponseEntity<Rule> updateRuleStatus(@PathVariable Long id, @RequestParam String status) {
        return ResponseEntity.ok(ruleService.updateRuleStatus(id, status));
    }
}
