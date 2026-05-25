package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.entity.SatisfactionAlert;
import com.property.repair.service.SatisfactionAlertService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/satisfaction-alert")
@CrossOrigin
public class SatisfactionAlertController {

    @Autowired
    private SatisfactionAlertService alertService;

    @GetMapping("/pending")
    public Result<List<SatisfactionAlert>> getPendingAlerts() {
        return Result.success(alertService.getPendingAlerts());
    }

    @GetMapping("/worker/{workerId}")
    public Result<List<SatisfactionAlert>> getWorkerAlerts(@PathVariable Long workerId) {
        return Result.success(alertService.getWorkerAlerts(workerId));
    }

    @GetMapping("/recent")
    public Result<List<SatisfactionAlert>> getRecentAlerts(
            @RequestParam(defaultValue = "7") int days) {
        return Result.success(alertService.getRecentAlerts(days));
    }

    @PostMapping("/handle/{alertId}")
    public Result<SatisfactionAlert> handleAlert(
            @PathVariable Long alertId,
            @RequestParam Long handlerId,
            @RequestParam String handlerName,
            @RequestParam(required = false) String remark,
            @RequestParam(defaultValue = "false") boolean completeTraining) {
        try {
            SatisfactionAlert alert = alertService.handleAlert(
                alertId, handlerId, handlerName, remark, completeTraining);
            return Result.success(alert);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/training-status/{workerId}")
    public Result<Map<String, Object>> checkTrainingStatus(@PathVariable Long workerId) {
        boolean inTraining = alertService.isWorkerInTraining(workerId);
        return Result.success(Map.of(
            "workerId", workerId,
            "inTraining", inTraining
        ));
    }
}
