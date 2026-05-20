package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.dto.TrendAnalysisDTO;
import com.payment.reconciliation.entity.DiscrepancyTrend;
import com.payment.reconciliation.service.TrendAnalysisService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/trend-analysis")
public class TrendAnalysisController {

    @Autowired
    private TrendAnalysisService trendAnalysisService;

    @PostMapping("/generate")
    public Result<Void> generateDailyTrendStatistics() {
        trendAnalysisService.generateDailyTrendStatistics();
        return Result.success();
    }

    @PostMapping("/data")
    public Result<List<DiscrepancyTrend>> getTrendData(@RequestBody TrendAnalysisDTO dto) {
        List<DiscrepancyTrend> list = trendAnalysisService.getTrendData(dto);
        return Result.success(list);
    }

    @PostMapping("/chart-data")
    public Result<Map<String, Object>> getTrendChartData(@RequestBody TrendAnalysisDTO dto) {
        Map<String, Object> data = trendAnalysisService.getTrendChartData(dto);
        return Result.success(data);
    }

    @PostMapping("/type-distribution")
    public Result<Map<String, Object>> getDiscrepancyTypeDistribution(@RequestBody TrendAnalysisDTO dto) {
        Map<String, Object> data = trendAnalysisService.getDiscrepancyTypeDistribution(dto);
        return Result.success(data);
    }
}
