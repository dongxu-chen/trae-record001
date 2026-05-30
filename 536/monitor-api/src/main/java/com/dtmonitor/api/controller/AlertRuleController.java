package com.dtmonitor.api.controller;

import com.dtmonitor.alert.rule.AlertRule;
import com.dtmonitor.alert.service.AlertEngine;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/alert-rules")
@RequiredArgsConstructor
public class AlertRuleController {

    private final AlertEngine alertEngine;

    @GetMapping
    public ResponseEntity<List<AlertRule>> getRules() {
        return ResponseEntity.ok(alertEngine.getRules());
    }

    @PostMapping
    public ResponseEntity<Void> addRule(@RequestBody AlertRule rule) {
        alertEngine.addRule(rule);
        return ResponseEntity.ok().build();
    }

    @DeleteMapping("/{ruleName}")
    public ResponseEntity<Void> removeRule(@PathVariable String ruleName) {
        alertEngine.removeRule(ruleName);
        return ResponseEntity.ok().build();
    }

    @PutMapping("/timeout-threshold")
    public ResponseEntity<Void> updateTimeoutThreshold(@RequestParam long thresholdMs) {
        alertEngine.updateTimeoutThreshold(thresholdMs);
        return ResponseEntity.ok().build();
    }
}
