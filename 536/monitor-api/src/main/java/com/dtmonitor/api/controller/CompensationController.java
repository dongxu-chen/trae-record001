package com.dtmonitor.api.controller;

import com.dtmonitor.diagnosis.model.CompensationRecommendation;
import com.dtmonitor.diagnosis.service.CompensationRecommendationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/compensation")
@RequiredArgsConstructor
public class CompensationController {

    private final CompensationRecommendationService recommendationService;

    @GetMapping("/{xid}")
    public ResponseEntity<CompensationRecommendation> getRecommendation(@PathVariable String xid) {
        CompensationRecommendation recommendation = recommendationService.getRecommendation(xid);
        if (recommendation == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(recommendation);
    }

    @PostMapping("/{xid}/execute")
    public ResponseEntity<Map<String, Object>> executeStrategy(
            @PathVariable String xid,
            @RequestParam String strategyType) {
        Map<String, Object> result = recommendationService.executeStrategy(xid, strategyType);
        boolean success = (Boolean) result.getOrDefault("success", false);
        if (success) {
            return ResponseEntity.ok(result);
        } else {
            return ResponseEntity.badRequest().body(result);
        }
    }
}
