package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.service.StatisticsService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/statistics")
@CrossOrigin
public class StatisticsController {

    @Autowired
    private StatisticsService statisticsService;

    @GetMapping("/overview")
    public Result<Map<String, Object>> overview() {
        return Result.success(statisticsService.getOverview());
    }

    @GetMapping("/type")
    public Result<Map<String, Long>> typeStatistics() {
        return Result.success(statisticsService.getTypeStatistics());
    }

    @GetMapping("/daily")
    public Result<Map<String, Long>> dailyStatistics(@RequestParam(defaultValue = "30") int days) {
        return Result.success(statisticsService.getDailyStatistics(days));
    }

    @GetMapping("/worker")
    public Result<List<Map<String, Object>>> workerStatistics() {
        return Result.success(statisticsService.getWorkerStatistics());
    }
}
