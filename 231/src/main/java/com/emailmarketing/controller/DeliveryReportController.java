package com.emailmarketing.controller;

import com.emailmarketing.common.Result;
import com.emailmarketing.entity.DeliveryReport;
import com.emailmarketing.service.DeliveryReportService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/delivery-report")
public class DeliveryReportController {

    @Autowired
    private DeliveryReportService reportService;

    @GetMapping("/overall")
    public Result<Map<String, Object>> getOverallStats(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        return Result.success(reportService.getOverallDeliveryStats(startDate, endDate));
    }

    @GetMapping("/domain")
    public Result<List<DeliveryReport>> getDomainReport(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        return Result.success(reportService.getDomainReportSummary(startDate, endDate));
    }

    @GetMapping("/task/{taskId}")
    public Result<List<DeliveryReport>> getTaskReport(
            @PathVariable Long taskId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        return Result.success(reportService.getTaskReport(taskId, startDate, endDate));
    }

    @PostMapping("/generate/daily")
    public Result<Void> generateDailyReport(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate reportDate) {
        reportService.generateDailyReport(reportDate);
        return Result.success();
    }

    @PostMapping("/generate/task/{taskId}")
    public Result<Void> generateTaskReport(
            @PathVariable Long taskId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate reportDate) {
        reportService.generateTaskReport(taskId, reportDate);
        return Result.success();
    }
}
