package com.property.repair.controller;

import com.property.repair.common.Result;
import com.property.repair.entity.RepairLog;
import com.property.repair.service.RepairLogService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/log")
@CrossOrigin
public class LogController {

    @Autowired
    private RepairLogService logService;

    @GetMapping("/order/{orderId}")
    public Result<List<RepairLog>> getOrderLogs(@PathVariable Long orderId) {
        return Result.success(logService.getOrderLogs(orderId));
    }
}
