package com.datasecurity.masking.controller;

import com.datasecurity.masking.rule.CustomMaskRule;
import com.datasecurity.masking.rule.RuleManagementService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/rules")
public class RuleController {

    @Autowired
    private RuleManagementService ruleManagementService;

    @GetMapping
    public ResponseEntity<List<CustomMaskRule>> getAllRules() {
        return ResponseEntity.ok(ruleManagementService.getAllRules());
    }

    @GetMapping("/enabled")
    public ResponseEntity<List<CustomMaskRule>> getEnabledRules() {
        return ResponseEntity.ok(ruleManagementService.getEnabledRules());
    }

    @GetMapping("/{ruleId}")
    public ResponseEntity<CustomMaskRule> getRuleById(@PathVariable String ruleId) {
        CustomMaskRule rule = ruleManagementService.getRuleById(ruleId);
        if (rule == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(rule);
    }

    @PostMapping
    public ResponseEntity<Void> addRule(@RequestBody CustomMaskRule rule) {
        ruleManagementService.addRule(rule);
        return ResponseEntity.ok().build();
    }

    @DeleteMapping("/{ruleId}")
    public ResponseEntity<Void> removeRule(@PathVariable String ruleId) {
        boolean removed = ruleManagementService.removeRule(ruleId);
        if (removed) {
            return ResponseEntity.ok().build();
        }
        return ResponseEntity.notFound().build();
    }

    @PostMapping("/match/column")
    public ResponseEntity<CustomMaskRule> matchByColumn(
            @RequestParam String columnName,
            @RequestParam(required = false) String comment) {
        CustomMaskRule rule = ruleManagementService.matchByColumn(columnName, comment);
        if (rule == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(rule);
    }

    @PostMapping("/match/value")
    public ResponseEntity<CustomMaskRule> matchByValue(@RequestBody String value) {
        CustomMaskRule rule = ruleManagementService.matchByValue(value);
        if (rule == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(rule);
    }
}
