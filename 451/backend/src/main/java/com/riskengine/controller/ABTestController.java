package com.riskengine.controller;

import com.riskengine.engine.abtest.ABTestService;
import com.riskengine.model.ABTestExperiment;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/abtest")
@CrossOrigin(origins = "*")
public class ABTestController {

    private final ABTestService abTestService;

    public ABTestController(ABTestService abTestService) {
        this.abTestService = abTestService;
    }

    @PostMapping
    public ResponseEntity<ABTestExperiment> createExperiment(@RequestBody ABTestExperiment experiment) {
        return ResponseEntity.ok(abTestService.createExperiment(experiment));
    }

    @GetMapping
    public ResponseEntity<List<ABTestExperiment>> getAllExperiments() {
        return ResponseEntity.ok(abTestService.getAllExperiments());
    }

    @GetMapping("/{id}")
    public ResponseEntity<ABTestExperiment> getExperiment(@PathVariable Long id) {
        ABTestExperiment exp = abTestService.getExperiment(id);
        return exp != null ? ResponseEntity.ok(exp) : ResponseEntity.notFound().build();
    }

    @PostMapping("/{id}/start")
    public ResponseEntity<Map<String, String>> startExperiment(@PathVariable Long id) {
        abTestService.startExperiment(id);
        return ResponseEntity.ok(Map.of("status", "success", "message", "Experiment started"));
    }

    @PostMapping("/{id}/stop")
    public ResponseEntity<Map<String, String>> stopExperiment(@PathVariable Long id) {
        abTestService.stopExperiment(id);
        return ResponseEntity.ok(Map.of("status", "success", "message", "Experiment stopped"));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteExperiment(@PathVariable Long id) {
        abTestService.deleteExperiment(id);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{id}/stats")
    public ResponseEntity<Map<String, Object>> getExperimentStats(@PathVariable Long id) {
        return ResponseEntity.ok(abTestService.getExperimentStats(id));
    }
}
