package com.sla.monitor.controller;

import com.sla.monitor.dto.PredictionResultDTO;
import com.sla.monitor.dto.RootCauseResultDTO;
import com.sla.monitor.dto.ServiceComparisonDTO;
import com.sla.monitor.engine.CalendarWindowMetrics;
import com.sla.monitor.model.SlaMetrics;
import com.sla.monitor.service.*;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/metrics")
public class SlaMetricsController {

    private final SlaCalculationService slaCalculationService;
    private final TimeSeriesPredictionService predictionService;
    private final RootCauseAnalysisService rootCauseAnalysisService;
    private final DataGeneratorService dataGeneratorService;

    public SlaMetricsController(SlaCalculationService slaCalculationService,
                                 TimeSeriesPredictionService predictionService,
                                 RootCauseAnalysisService rootCauseAnalysisService,
                                 DataGeneratorService dataGeneratorService) {
        this.slaCalculationService = slaCalculationService;
        this.predictionService = predictionService;
        this.rootCauseAnalysisService = rootCauseAnalysisService;
        this.dataGeneratorService = dataGeneratorService;
    }

    @GetMapping("/{serviceName}/latest")
    public ResponseEntity<SlaMetrics> getLatestMetrics(@PathVariable String serviceName) {
        SlaMetrics metrics = slaCalculationService.getLatestMetrics(serviceName);
        return metrics != null ? ResponseEntity.ok(metrics) : ResponseEntity.notFound().build();
    }

    @GetMapping("/{serviceName}/history")
    public List<SlaMetrics> getMetricsHistory(
            @PathVariable String serviceName,
            @RequestParam(defaultValue = "24") int hours,
            @RequestParam(required = false) CalendarWindowMetrics.WindowType windowType) {
        if (windowType != null) {
            return slaCalculationService.getMetricsHistoryByWindowType(serviceName, windowType, hours);
        }
        return slaCalculationService.getMetricsHistory(serviceName, hours);
    }

    @GetMapping("/{serviceName}/windows")
    public Map<String, CalendarWindowMetrics.WindowMetrics> getAllWindowMetrics(@PathVariable String serviceName) {
        Map<CalendarWindowMetrics.WindowType, CalendarWindowMetrics.WindowMetrics> metrics = 
                slaCalculationService.getAllWindowMetrics(serviceName);
        
        Map<String, CalendarWindowMetrics.WindowMetrics> result = new HashMap<>();
        for (Map.Entry<CalendarWindowMetrics.WindowType, CalendarWindowMetrics.WindowMetrics> entry : metrics.entrySet()) {
            result.put(entry.getKey().name(), entry.getValue());
        }
        return result;
    }

    @GetMapping("/{serviceName}/window/{windowType}")
    public CalendarWindowMetrics.WindowMetrics getWindowMetrics(
            @PathVariable String serviceName,
            @PathVariable CalendarWindowMetrics.WindowType windowType) {
        return slaCalculationService.getWindowMetrics(serviceName, windowType);
    }

    @GetMapping("/window-bounds/{windowType}")
    public CalendarWindowMetrics.WindowBounds getWindowBounds(
            @PathVariable CalendarWindowMetrics.WindowType windowType) {
        return slaCalculationService.getWindowBounds(windowType);
    }

    @GetMapping("/{serviceName}/availability-summary")
    public Map<String, Double> getAvailabilitySummary(@PathVariable String serviceName) {
        Map<String, Double> summary = new HashMap<>();
        summary.put("daily", slaCalculationService.calculateDailyAvailability(serviceName));
        summary.put("weekly", slaCalculationService.calculateWeeklyAvailability(serviceName));
        summary.put("monthly", slaCalculationService.calculateMonthlyAvailability(serviceName));
        return summary;
    }

    @GetMapping("/compare")
    public List<ServiceComparisonDTO> compareServices(
            @RequestParam List<String> serviceNames,
            @RequestParam(defaultValue = "1") int hours) {
        List<SlaMetrics> metricsList = slaCalculationService.compareServices(serviceNames, hours);
        List<ServiceComparisonDTO> result = new ArrayList<>();
        
        for (SlaMetrics metrics : metricsList) {
            ServiceComparisonDTO dto = new ServiceComparisonDTO();
            dto.setServiceName(metrics.getServiceName());
            dto.setAvailability(metrics.getAvailability());
            dto.setAvgLatencyMs(metrics.getAvgLatencyMs());
            dto.setErrorRate(metrics.getErrorRate());
            dto.setSlaAchievementRate(metrics.getSlaAchievementRate());
            dto.setSlaViolated(metrics.isSlaViolated());
            result.add(dto);
        }
        
        return result;
    }

    @GetMapping("/{serviceName}/prediction")
    public PredictionResultDTO getPrediction(@PathVariable String serviceName) {
        return predictionService.predictSlaTrend(serviceName);
    }

    @GetMapping("/{serviceName}/root-cause")
    public RootCauseResultDTO getRootCauseAnalysis(@PathVariable String serviceName) {
        return rootCauseAnalysisService.performRootCauseAnalysis(serviceName);
    }

    @PostMapping("/{serviceName}/simulate")
    public ResponseEntity<String> simulateRequest(
            @PathVariable String serviceName,
            @RequestParam(defaultValue = "100") int count) {
        dataGeneratorService.generateRequests(serviceName, count);
        return ResponseEntity.ok("Generated " + count + " requests for " + serviceName);
    }

    @PostMapping("/simulate-all")
    public ResponseEntity<String> simulateAllServices() {
        dataGeneratorService.generateHistoricalData();
        return ResponseEntity.ok("Generated historical data for all services");
    }
}
