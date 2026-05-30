package com.riskengine.controller;

import com.riskengine.model.*;
import com.riskengine.service.RuleService;
import com.riskengine.service.StatsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/rules")
@CrossOrigin(origins = "*")
public class RuleController {

    private final RuleService ruleService;

    public RuleController(RuleService ruleService) {
        this.ruleService = ruleService;
    }

    @PostMapping
    public ResponseEntity<RuleDefinition> createRule(@RequestBody RuleDefinition rule) {
        return ResponseEntity.ok(ruleService.createRule(rule));
    }

    @PutMapping("/{id}")
    public ResponseEntity<RuleDefinition> updateRule(@PathVariable Long id, @RequestBody RuleDefinition rule) {
        return ResponseEntity.ok(ruleService.updateRule(id, rule));
    }

    @GetMapping("/{id}")
    public ResponseEntity<RuleDefinition> getRule(@PathVariable Long id) {
        return ruleService.getRule(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/code/{ruleCode}")
    public ResponseEntity<RuleDefinition> getRuleByCode(@PathVariable String ruleCode) {
        return ruleService.getRuleByCode(ruleCode)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping
    public ResponseEntity<List<RuleDefinition>> getAllRules() {
        return ResponseEntity.ok(ruleService.getAllRules());
    }

    @GetMapping("/enabled")
    public ResponseEntity<List<RuleDefinition>> getEnabledRules() {
        return ResponseEntity.ok(ruleService.getEnabledRules());
    }

    @GetMapping("/scene/{sceneCode}")
    public ResponseEntity<List<RuleDefinition>> getRulesByScene(@PathVariable String sceneCode) {
        return ResponseEntity.ok(ruleService.getRulesByScene(sceneCode));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteRule(@PathVariable Long id) {
        ruleService.deleteRule(id);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{id}/versions")
    public ResponseEntity<List<RuleVersion>> getVersionHistory(@PathVariable Long id) {
        return ResponseEntity.ok(ruleService.getVersionHistory(id));
    }

    @PostMapping("/{id}/rollback/{version}")
    public ResponseEntity<RuleDefinition> rollback(@PathVariable Long id, @PathVariable Integer version) {
        return ResponseEntity.ok(ruleService.rollback(id, version));
    }

    @PostMapping("/hot-reload")
    public ResponseEntity<Map<String, String>> hotReloadAll() {
        ruleService.hotReloadAll();
        return ResponseEntity.ok(Map.of("status", "success", "message", "All rules hot reloaded"));
    }

    @PostMapping("/validate/drl")
    public ResponseEntity<Map<String, Object>> validateDrl(@RequestBody Map<String, String> body) {
        String drl = body.get("drl");
        boolean valid = ruleService.validateDrl(drl);
        return ResponseEntity.ok(Map.of("valid", valid));
    }

    @PostMapping("/validate/groovy")
    public ResponseEntity<Map<String, Object>> validateGroovy(@RequestBody Map<String, String> body) {
        String script = body.get("script");
        boolean valid = ruleService.validateGroovy(script);
        return ResponseEntity.ok(Map.of("valid", valid));
    }

    @PostMapping("/simulate")
    public ResponseEntity<RiskDecision> simulate(@RequestBody SimulateRequest request) {
        return ResponseEntity.ok(ruleService.simulate(request));
    }

    @GetMapping("/classloader/stats")
    public ResponseEntity<Map<String, Object>> getClassLoaderStats() {
        return ResponseEntity.ok(ruleService.getGroovyClassLoaderStats());
    }

    @PostMapping("/classloader/cleanup")
    public ResponseEntity<Map<String, String>> triggerClassLoaderCleanup() {
        ruleService.triggerClassLoaderCleanup();
        return ResponseEntity.ok(Map.of("status", "success", "message", "ClassLoader cleanup triggered"));
    }
}
