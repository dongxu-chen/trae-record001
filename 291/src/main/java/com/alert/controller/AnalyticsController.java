package com.alert.controller;

import com.alert.dto.ReportDTO;
import com.alert.entity.AlertEvent;
import com.alert.entity.AlertPrediction;
import com.alert.entity.AlertRootCause;
import com.alert.service.AlertPredictionService;
import com.alert.service.ReportService;
import com.alert.service.RootCauseAnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/analytics")
@CrossOrigin(origins = "*")
public class AnalyticsController {

    @Autowired
    private RootCauseAnalysisService rootCauseService;

    @Autowired
    private AlertPredictionService predictionService;

    @Autowired
    private ReportService reportService;

    @GetMapping("/root-causes")
    public ResponseEntity<List<AlertRootCause>> getAllRootCauses() {
        return ResponseEntity.ok(rootCauseService.getAllRootCauses());
    }

    @GetMapping("/root-causes/{rootCauseId}")
    public ResponseEntity<AlertRootCause> getRootCauseById(@PathVariable String rootCauseId) {
        return ResponseEntity.ok(rootCauseService.getRootCauseById(rootCauseId));
    }

    @GetMapping("/root-causes/{rootCauseId}/affected-alerts")
    public ResponseEntity<List<AlertEvent>> getAffectedAlerts(@PathVariable String rootCauseId) {
        return ResponseEntity.ok(rootCauseService.getAffectedAlerts(rootCauseId));
    }

    @PostMapping("/root-causes/{rootCauseId}/confirm")
    public ResponseEntity<AlertRootCause> confirmRootCause(@PathVariable String rootCauseId) {
        return ResponseEntity.ok(rootCauseService.confirmRootCause(rootCauseId));
    }

    @PostMapping("/root-causes/{rootCauseId}/reject")
    public ResponseEntity<AlertRootCause> rejectRootCause(@PathVariable String rootCauseId) {
        return ResponseEntity.ok(rootCauseService.rejectRootCause(rootCauseId));
    }

    @PostMapping("/root-causes/analyze")
    public ResponseEntity<Void> triggerRootCauseAnalysis() {
        rootCauseService.analyzeRootCauses();
        return ResponseEntity.ok().build();
    }

    @GetMapping("/predictions")
    public ResponseEntity<List<AlertPrediction>> getAllPredictions() {
        return ResponseEntity.ok(predictionService.getAllPredictions());
    }

    @GetMapping("/predictions/{predictionId}")
    public ResponseEntity<AlertPrediction> getPredictionById(@PathVariable String predictionId) {
        return ResponseEntity.ok(predictionService.getPredictionById(predictionId));
    }

    @PostMapping("/predictions/{predictionId}/confirm")
    public ResponseEntity<AlertPrediction> confirmPrediction(
            @PathVariable String predictionId,
            @RequestBody(required = false) Map<String, String> body) {
        String actualAlertId = body != null ? body.get("actualAlertId") : null;
        return ResponseEntity.ok(predictionService.confirmPrediction(predictionId, actualAlertId));
    }

    @PostMapping("/predictions/{predictionId}/dismiss")
    public ResponseEntity<AlertPrediction> dismissPrediction(@PathVariable String predictionId) {
        return ResponseEntity.ok(predictionService.dismissPrediction(predictionId));
    }

    @PostMapping("/predictions/generate")
    public ResponseEntity<Void> generatePredictions() {
        predictionService.generatePredictions();
        return ResponseEntity.ok().build();
    }

    @GetMapping("/report")
    public ResponseEntity<ReportDTO> getReport(
            @RequestParam(defaultValue = "7") int days) {
        return ResponseEntity.ok(reportService.generateReport(days));
    }
}
