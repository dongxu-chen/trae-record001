package com.emailmarketing.controller;

import com.emailmarketing.common.Result;
import com.emailmarketing.entity.EmailStatistics;
import com.emailmarketing.service.EmailStatisticsService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/statistics")
public class EmailStatisticsController {

    @Autowired
    private EmailStatisticsService statisticsService;

    @GetMapping("/task/{taskId}")
    public Result<EmailStatistics> getTaskStatistics(@PathVariable Long taskId) {
        return Result.success(statisticsService.getTaskStatistics(taskId));
    }

    @GetMapping("/task/{taskId}/range")
    public Result<List<EmailStatistics>> getTaskStatisticsByDateRange(
            @PathVariable Long taskId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        return Result.success(statisticsService.getTaskStatisticsByDateRange(taskId, startDate, endDate));
    }
}
