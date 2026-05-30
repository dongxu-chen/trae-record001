package com.riskengine.controller;

import com.riskengine.model.HitStats;
import com.riskengine.service.StatsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/stats")
@CrossOrigin(origins = "*")
public class StatsController {

    private final StatsService statsService;

    public StatsController(StatsService statsService) {
        this.statsService = statsService;
    }

    @GetMapping("/hit")
    public ResponseEntity<List<HitStats>> getHitStats() {
        return ResponseEntity.ok(statsService.getHitStats());
    }

    @GetMapping("/actions")
    public ResponseEntity<Map<String, Long>> getActionCounts() {
        return ResponseEntity.ok(statsService.getActionCounts());
    }

    @GetMapping("/dashboard")
    public ResponseEntity<Map<String, Object>> getDashboardStats() {
        return ResponseEntity.ok(statsService.getDashboardStats());
    }

    @GetMapping("/hit/granularity/{granularity}")
    public ResponseEntity<Map<String, Object>> getHitStatsByGranularity(
            @PathVariable String granularity,
            @RequestParam(required = false) List<String> ruleCodes) {
        if (ruleCodes != null && !ruleCodes.isEmpty()) {
            return ResponseEntity.ok(statsService.getTimeSeriesData(granularity, ruleCodes));
        }
        return ResponseEntity.ok(statsService.getHitStatsByGranularity(granularity));
    }

    @GetMapping("/actions/granularity/{granularity}")
    public ResponseEntity<Map<String, Long>> getActionCountsByGranularity(@PathVariable String granularity) {
        return ResponseEntity.ok(statsService.getActionCountsByGranularity(granularity));
    }
}
