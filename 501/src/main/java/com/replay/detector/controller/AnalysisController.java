package com.replay.detector.controller;

import com.replay.detector.dto.ApiResponse;
import com.replay.detector.model.AdaptiveThresholdState;
import com.replay.detector.model.AttackTrace;
import com.replay.detector.model.TrendReport;
import com.replay.detector.service.AdaptiveThresholdService;
import com.replay.detector.service.AttackTracingService;
import com.replay.detector.service.TrendAnalysisService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/replay")
@RequiredArgsConstructor
public class AnalysisController {

    private final AttackTracingService attackTracingService;
    private final AdaptiveThresholdService adaptiveThresholdService;
    private final TrendAnalysisService trendAnalysisService;

    @GetMapping("/trace/{clientIp}")
    public ApiResponse<AttackTrace> getTrace(@PathVariable String clientIp) {
        AttackTrace trace = attackTracingService.getTrace(clientIp);
        return ApiResponse.success(trace);
    }

    @GetMapping("/trace/top-attackers")
    public ApiResponse<List<AttackTrace>> getTopAttackers(
            @RequestParam(defaultValue = "10") int limit) {
        List<AttackTrace> attackers = attackTracingService.getTopAttackers(limit);
        return ApiResponse.success(attackers);
    }

    @GetMapping("/adaptive/state")
    public ApiResponse<AdaptiveThresholdState> getAdaptiveState() {
        AdaptiveThresholdState state = adaptiveThresholdService.getCurrentState();
        return ApiResponse.success(state);
    }

    @PostMapping("/adaptive/refresh")
    public ApiResponse<AdaptiveThresholdState> refreshAdaptiveThreshold() {
        AdaptiveThresholdState state = adaptiveThresholdService.refreshState();
        return ApiResponse.success(state);
    }

    @GetMapping("/trend/report")
    public ApiResponse<TrendReport> getTrendReport(
            @RequestParam(required = false) Long periodStart,
            @RequestParam(required = false) Long periodEnd) {
        TrendReport report = trendAnalysisService.generateReport(
                periodStart != null ? periodStart : 0,
                periodEnd != null ? periodEnd : 0);
        return ApiResponse.success(report);
    }

    @GetMapping("/trend/peak-hours")
    public ApiResponse<List<TrendReport.HourlyDistribution>> getPeakHours(
            @RequestParam(defaultValue = "5") int topN) {
        List<TrendReport.HourlyDistribution> peakHours = trendAnalysisService.getPeakHours(topN);
        return ApiResponse.success(peakHours);
    }
}
