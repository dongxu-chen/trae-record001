package com.ratelimit.recommender.controller;

import com.ratelimit.recommender.model.*;
import com.ratelimit.recommender.service.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/evaluation")
@CrossOrigin(origins = "*")
public class EvaluationController {

    private final RateLimitEvaluationService evaluationService;

    public EvaluationController(RateLimitEvaluationService evaluationService) {
        this.evaluationService = evaluationService;
    }

    @PostMapping("/{serviceId}")
    public ResponseEntity<RateLimitEvaluation> evaluate(
            @PathVariable String serviceId,
            @RequestParam(defaultValue = "30") int durationMinutes) {
        return ResponseEntity.ok(evaluationService.evaluate(serviceId, durationMinutes));
    }

    @PostMapping("/all")
    public ResponseEntity<List<RateLimitEvaluation>> evaluateAll(
            @RequestParam(defaultValue = "30") int durationMinutes) {
        return ResponseEntity.ok(evaluationService.evaluateAllServices(durationMinutes));
    }

    @GetMapping("/history")
    public ResponseEntity<List<RateLimitEvaluation>> getHistory() {
        return ResponseEntity.ok(evaluationService.getAllEvaluations());
    }

    @GetMapping("/{evaluationId}")
    public ResponseEntity<RateLimitEvaluation> getEvaluation(@PathVariable String evaluationId) {
        RateLimitEvaluation evaluation = evaluationService.getEvaluation(evaluationId);
        if (evaluation == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(evaluation);
    }
}
