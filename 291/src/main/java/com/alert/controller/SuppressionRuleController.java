package com.alert.controller;

import com.alert.entity.AlertSuppressionRule;
import com.alert.service.SuppressionRuleService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/suppression-rules")
@CrossOrigin(origins = "*")
public class SuppressionRuleController {

    @Autowired
    private SuppressionRuleService ruleService;

    @GetMapping
    public ResponseEntity<List<AlertSuppressionRule>> getAllRules() {
        return ResponseEntity.ok(ruleService.getAllRules());
    }

    @GetMapping("/{id}")
    public ResponseEntity<AlertSuppressionRule> getRuleById(@PathVariable Long id) {
        return ResponseEntity.ok(ruleService.getRuleById(id));
    }

    @PostMapping
    public ResponseEntity<AlertSuppressionRule> createRule(@RequestBody AlertSuppressionRule rule) {
        return ResponseEntity.ok(ruleService.createRule(rule));
    }

    @PutMapping("/{id}")
    public ResponseEntity<AlertSuppressionRule> updateRule(
            @PathVariable Long id,
            @RequestBody AlertSuppressionRule rule) {
        return ResponseEntity.ok(ruleService.updateRule(id, rule));
    }

    @PatchMapping("/{id}/position")
    public ResponseEntity<AlertSuppressionRule> updatePosition(
            @PathVariable Long id,
            @RequestBody Map<String, Integer> position) {
        return ResponseEntity.ok(ruleService.updateRulePosition(
                id,
                position.get("positionX"),
                position.get("positionY")
        ));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteRule(@PathVariable Long id) {
        ruleService.deleteRule(id);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/{id}/toggle")
    public ResponseEntity<AlertSuppressionRule> toggleRule(@PathVariable Long id) {
        return ResponseEntity.ok(ruleService.toggleRule(id));
    }
}
