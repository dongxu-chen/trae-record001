package com.risk.engine.controller;

import com.risk.engine.entity.EasyRule;
import com.risk.engine.repository.EasyRuleRepository;
import com.risk.engine.rules.DynamicRuleEngine;
import com.risk.engine.rules.RuleDefinition;
import com.risk.engine.rules.YamlRuleParser;
import com.risk.engine.service.EasyDecisionService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/rules")
@Api(tags = "规则管理(EasyRules)")
public class EasyRuleController {

    @Autowired
    private EasyRuleRepository ruleRepository;

    @Autowired
    private DynamicRuleEngine ruleEngine;

    @Autowired
    private YamlRuleParser yamlRuleParser;

    @Autowired
    private EasyDecisionService decisionService;

    @PostMapping
    @ApiOperation("创建规则")
    public ResponseEntity<EasyRule> createRule(@RequestBody EasyRule rule) {
        rule.setStatus("DISABLED");
        EasyRule saved = ruleRepository.save(rule);
        return ResponseEntity.ok(saved);
    }

    @GetMapping("/{id}")
    @ApiOperation("根据ID查询规则")
    public ResponseEntity<EasyRule> getRuleById(@PathVariable Long id) {
        return ruleRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    @ApiOperation("查询所有规则")
    public ResponseEntity<List<EasyRule>> getAllRules() {
        return ResponseEntity.ok(ruleRepository.findAll());
    }

    @PutMapping("/{id}")
    @ApiOperation("更新规则")
    public ResponseEntity<EasyRule> updateRule(@PathVariable Long id, @RequestBody EasyRule rule) {
        if (!ruleRepository.existsById(id)) {
            return ResponseEntity.notFound().build();
        }
        rule.setId(id);
        EasyRule updated = ruleRepository.save(rule);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除规则")
    public ResponseEntity<Void> deleteRule(@PathVariable Long id) {
        Optional<EasyRule> ruleOpt = ruleRepository.findById(id);
        if (ruleOpt.isPresent()) {
            EasyRule rule = ruleOpt.get();
            ruleEngine.removeRule(rule.getScene(), rule.getRuleCode());
            ruleRepository.deleteById(id);
        }
        return ResponseEntity.ok().build();
    }

    @PatchMapping("/{id}/status")
    @ApiOperation("更新规则状态")
    public ResponseEntity<EasyRule> updateRuleStatus(@PathVariable Long id, @RequestParam String status) {
        Optional<EasyRule> ruleOpt = ruleRepository.findById(id);
        if (ruleOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        
        EasyRule rule = ruleOpt.get();
        rule.setStatus(status);
        EasyRule updated = ruleRepository.save(rule);
        
        if ("ENABLED".equals(status)) {
            ruleEngine.addRule(updated);
        } else {
            ruleEngine.removeRule(updated.getScene(), updated.getRuleCode());
        }
        
        return ResponseEntity.ok(updated);
    }

    @PostMapping("/import/yaml")
    @ApiOperation("从YAML导入规则")
    public ResponseEntity<List<EasyRule>> importRulesFromYaml(@RequestBody String yamlContent) {
        List<RuleDefinition> definitions = yamlRuleParser.parseYaml(yamlContent);
        List<EasyRule> rules = new java.util.ArrayList<>();
        for (RuleDefinition def : definitions) {
            EasyRule entity = yamlRuleParser.toEntity(def);
            entity.setYamlContent(yamlContent);
            EasyRule saved = ruleRepository.save(entity);
            rules.add(saved);
            if ("ENABLED".equals(saved.getStatus())) {
                ruleEngine.addRule(saved);
            }
        }
        return ResponseEntity.ok(rules);
    }

    @GetMapping("/export/yaml/{id}")
    @ApiOperation("导出规则为YAML")
    public ResponseEntity<String> exportRuleToYaml(@PathVariable Long id) {
        return ruleRepository.findById(id)
                .map(rule -> {
                    RuleDefinition def = yamlRuleParser.fromEntity(rule);
                    String yaml = yamlRuleParser.toYaml(java.util.Collections.singletonList(def));
                    return ResponseEntity.ok(yaml);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/reload")
    @ApiOperation("热部署所有规则")
    public ResponseEntity<Map<String, Object>> reloadAllRules() {
        boolean success = decisionService.reloadAllRules();
        Map<String, Object> result = new HashMap<>();
        result.put("success", success);
        result.put("status", decisionService.getEngineStatus());
        return ResponseEntity.ok(result);
    }

    @PostMapping("/reload/{scene}")
    @ApiOperation("热部署指定场景的规则")
    public ResponseEntity<Map<String, Object>> reloadRulesByScene(@PathVariable String scene) {
        boolean success = decisionService.reloadRules(scene);
        Map<String, Object> result = new HashMap<>();
        result.put("success", success);
        result.put("scene", scene);
        result.put("ruleCount", ruleEngine.getRuleCount(scene));
        result.put("version", ruleEngine.getRuleVersion(scene));
        return ResponseEntity.ok(result);
    }

    @GetMapping("/status")
    @ApiOperation("获取规则引擎状态")
    public ResponseEntity<Map<String, Object>> getEngineStatus() {
        return ResponseEntity.ok(decisionService.getEngineStatus());
    }

    @GetMapping("/scene/{scene}")
    @ApiOperation("按场景查询规则")
    public ResponseEntity<List<EasyRule>> getRulesByScene(@PathVariable String scene) {
        return ResponseEntity.ok(ruleEngine.getRulesByScene(scene));
    }

    @PostMapping("/validate")
    @ApiOperation("验证规则表达式")
    public ResponseEntity<Map<String, Object>> validateRuleExpression(@RequestBody Map<String, String> request) {
        String condition = request.get("condition");
        String action = request.get("action");
        
        Map<String, Object> result = new HashMap<>();
        
        if (condition != null) {
            boolean conditionValid = yamlRuleParser.validateExpression(condition);
            result.put("conditionValid", conditionValid);
        }
        
        if (action != null) {
            boolean actionValid = yamlRuleParser.validateExpression(action);
            result.put("actionValid", actionValid);
        }
        
        return ResponseEntity.ok(result);
    }
}
