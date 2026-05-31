package com.checkin.controller;

import com.checkin.common.Result;
import com.checkin.entity.CheckinAnalysis;
import com.checkin.service.AnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.Map;

@RestController
@RequestMapping("/api/analysis")
public class AnalysisController {

    @Autowired
    private AnalysisService analysisService;

    @GetMapping("/dashboard")
    public Result<Map<String, Object>> getDashboardStats() {
        try {
            Map<String, Object> stats = analysisService.getDashboardStats();
            return Result.success(stats);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/{periodType}")
    public Result<Map<String, Object>> getAnalysis(
            @PathVariable String periodType,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        try {
            Map<String, Object> analysis = analysisService.getAnalysis(periodType, startDate, endDate);
            return Result.success(analysis);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/generate/{periodType}")
    public Result<CheckinAnalysis> generateAnalysis(
            @PathVariable String periodType,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        try {
            if (date == null) {
                date = LocalDate.now();
            }
            CheckinAnalysis analysis = analysisService.generateAnalysis(periodType, date);
            return Result.success(analysis);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/user/{userId}")
    public Result<Map<String, Object>> getUserAnalysis(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "DAILY") String periodType) {
        try {
            Map<String, Object> analysis = analysisService.getUserAnalysis(userId, periodType);
            return Result.success(analysis);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/churn/{periodType}")
    public Result<Map<String, Object>> getChurnAnalysis(
            @PathVariable String periodType,
            @RequestParam(defaultValue = "30") int days) {
        try {
            LocalDate endDate = LocalDate.now();
            LocalDate startDate = endDate.minusDays(days);
            Map<String, Object> analysis = analysisService.getAnalysis(periodType, startDate, endDate);
            return Result.success((Map<String, Object>) analysis.get("churnAnalysis"));
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/trend/{periodType}")
    public Result<Map<String, Object>> getTrendAnalysis(
            @PathVariable String periodType,
            @RequestParam(defaultValue = "7") int days) {
        try {
            LocalDate endDate = LocalDate.now();
            LocalDate startDate = endDate.minusDays(days);
            Map<String, Object> analysis = analysisService.getAnalysis(periodType, startDate, endDate);
            
            Map<String, Object> result = Map.of(
                "trendData", analysis.get("trendData"),
                "avgCheckinRate", analysis.get("avgCheckinRate"),
                "totalCheckins", analysis.get("totalCheckins"),
                "avgChurnRate", analysis.get("avgChurnRate")
            );
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/report")
    public Result<Map<String, Object>> getFullReport(
            @RequestParam(defaultValue = "30") int days) {
        try {
            LocalDate endDate = LocalDate.now();
            LocalDate startDate = endDate.minusDays(days);
            
            Map<String, Object> dailyAnalysis = analysisService.getAnalysis("DAILY", startDate, endDate);
            Map<String, Object> weeklyAnalysis = analysisService.getAnalysis("WEEKLY", startDate, endDate);
            Map<String, Object> dashboard = analysisService.getDashboardStats();
            
            Map<String, Object> report = Map.of(
                "period", Map.of("startDate", startDate, "endDate", endDate, "days", days),
                "daily", dailyAnalysis,
                "weekly", weeklyAnalysis,
                "dashboard", dashboard,
                "summary", Map.of(
                    "avgDailyCheckinRate", dailyAnalysis.get("avgCheckinRate"),
                    "avgChurnRate", dailyAnalysis.get("avgChurnRate"),
                    "totalNewUsers", dailyAnalysis.get("totalNewUsers"),
                    "totalLostUsers", dailyAnalysis.get("totalLostUsers"),
                    "topChurnDay", ((Map<String, Object>) dailyAnalysis.get("churnAnalysis")).get("churnDay")
                )
            );
            
            return Result.success(report);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
}
