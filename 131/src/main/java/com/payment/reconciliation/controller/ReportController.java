package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.dto.ReportQueryDTO;
import com.payment.reconciliation.entity.ReconciliationResult;
import com.payment.reconciliation.service.ReportService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;

@RestController
@RequestMapping("/api/report")
public class ReportController {

    @Autowired
    private ReportService reportService;

    @PostMapping("/query")
    public Result<List<ReconciliationResult>> queryReconciliationResults(
            @RequestBody ReportQueryDTO dto) {
        List<ReconciliationResult> list = reportService.queryReconciliationResults(dto);
        return Result.success(list);
    }

    @GetMapping("/{id}")
    public Result<ReconciliationResult> getReconciliationResultById(@PathVariable Long id) {
        ReconciliationResult result = reportService.getReconciliationResultById(id);
        return Result.success(result);
    }

    @GetMapping("/export/{id}")
    public void exportReconciliationReport(@PathVariable Long id, HttpServletResponse response) throws IOException {
        reportService.exportReconciliationReport(id, response);
    }
}
