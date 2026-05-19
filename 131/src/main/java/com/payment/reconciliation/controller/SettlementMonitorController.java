package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.dto.TrendAnalysisDTO;
import com.payment.reconciliation.entity.SettlementMonitor;
import com.payment.reconciliation.service.SettlementMonitorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/settlement-monitor")
public class SettlementMonitorController {

    @Autowired
    private SettlementMonitorService settlementMonitorService;

    @PostMapping("/create/{channelCode}")
    public Result<Void> createSettlementMonitor(@PathVariable String channelCode) {
        settlementMonitorService.createSettlementMonitor(channelCode);
        return Result.success();
    }

    @GetMapping("/delayed")
    public Result<List<SettlementMonitor>> getDelayedSettlements(
            @RequestParam(required = false) Integer alertLevel) {
        List<SettlementMonitor> list = settlementMonitorService.getDelayedSettlements(alertLevel);
        return Result.success(list);
    }

    @PostMapping("/history")
    public Result<List<SettlementMonitor>> getSettlementHistory(@RequestBody TrendAnalysisDTO dto) {
        List<SettlementMonitor> list = settlementMonitorService.getSettlementHistory(dto);
        return Result.success(list);
    }

    @PostMapping("/confirm/{id}")
    public Result<Void> confirmSettlementArrival(@PathVariable Long id) {
        settlementMonitorService.confirmSettlementArrival(id);
        return Result.success();
    }
}
