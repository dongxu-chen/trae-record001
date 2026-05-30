package com.riskengine.controller;

import com.riskengine.engine.evaluation.RuleEffectEvaluator;
import com.riskengine.model.EffectEvaluation;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/evaluation")
@CrossOrigin(origins = "*")
public class EvaluationController {

    private final RuleEffectEvaluator evaluator;

    public EvaluationController(RuleEffectEvaluator evaluator) {
        this.evaluator = evaluator;
    }

    @GetMapping("/rule/{ruleCode}")
    public ResponseEntity<List<EffectEvaluation>> evaluateRule(
            @PathVariable String ruleCode,
            @RequestParam(defaultValue = "24") int beforeHours,
            @RequestParam(defaultValue = "24") int afterHours) {
        return ResponseEntity.ok(evaluator.evaluateRuleEffect(ruleCode, beforeHours, afterHours));
    }

    @GetMapping("/all")
    public ResponseEntity<List<EffectEvaluation>> evaluateAllRules(
            @RequestParam(defaultValue = "24") int beforeHours,
            @RequestParam(defaultValue = "24") int afterHours) {
        return ResponseEntity.ok(evaluator.evaluateAllRules(beforeHours, afterHours));
    }
}
