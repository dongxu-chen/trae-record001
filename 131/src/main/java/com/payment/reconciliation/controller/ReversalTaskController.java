package com.payment.reconciliation.controller;

import com.payment.reconciliation.common.Result;
import com.payment.reconciliation.entity.ReversalTask;
import com.payment.reconciliation.service.ReversalService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/reversal")
public class ReversalTaskController {

    @Autowired
    private ReversalService reversalService;

    @GetMapping("/list")
    public Result<List<ReversalTask>> listReversalTasks(
            @RequestParam(required = false) String channelCode,
            @RequestParam(required = false) Integer status) {
        List<ReversalTask> list = reversalService.listReversalTasks(channelCode, status);
        return Result.success(list);
    }

    @GetMapping("/{id}")
    public Result<ReversalTask> getReversalTaskById(@PathVariable Long id) {
        ReversalTask task = reversalService.getReversalTaskById(id);
        return Result.success(task);
    }

    @PostMapping("/execute/{id}")
    public Result<Void> executeReversalTask(@PathVariable Long id) {
        ReversalTask task = reversalService.getReversalTaskById(id);
        if (task == null) {
            return Result.fail("冲正任务不存在");
        }
        reversalService.executeReversalTask(task);
        return Result.success();
    }
}
