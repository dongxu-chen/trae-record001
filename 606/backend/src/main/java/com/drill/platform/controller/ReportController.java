package com.drill.platform.controller;

import com.drill.platform.model.ApiResult;
import com.drill.platform.model.DrillReport;
import com.drill.platform.service.DrillService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/report")
public class ReportController {

    private final DrillService drillService;

    public ReportController(DrillService drillService) {
        this.drillService = drillService;
    }

    @GetMapping
    public ApiResult<List<DrillReport>> listReports() {
        return ApiResult.success(drillService.listReports());
    }

    @GetMapping("/{taskId}")
    public ApiResult<DrillReport> getReport(@PathVariable String taskId) {
        DrillReport report = drillService.getReport(taskId);
        if (report == null) {
            return ApiResult.error(404, "Report not found");
        }
        return ApiResult.success(report);
    }
}
