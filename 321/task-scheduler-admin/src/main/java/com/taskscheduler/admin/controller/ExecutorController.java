package com.taskscheduler.admin.controller;

import com.taskscheduler.common.dto.PageResult;
import com.taskscheduler.common.dto.Result;
import com.taskscheduler.common.entity.ExecutorInfo;
import com.taskscheduler.core.service.ExecutorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/executor")
public class ExecutorController {

    @Autowired
    private ExecutorService executorService;

    @GetMapping("/list")
    public Result<PageResult<ExecutorInfo>> list(
            @RequestParam(defaultValue = "1") Integer pageNum,
            @RequestParam(defaultValue = "10") Integer pageSize,
            @RequestParam(required = false) String appName,
            @RequestParam(required = false) Integer status) {
        return Result.success(executorService.queryExecutors(pageNum, pageSize, appName, status));
    }

    @GetMapping("/{id}")
    public Result<ExecutorInfo> getById(@PathVariable Long id) {
        return Result.success(executorService.getExecutorById(id));
    }

    @GetMapping("/all")
    public Result<List<ExecutorInfo>> getAll() {
        return Result.success(executorService.getAllExecutors());
    }

    @GetMapping("/available")
    public Result<List<ExecutorInfo>> getAvailable() {
        return Result.success(executorService.getAvailableExecutors());
    }

    @PostMapping("/add")
    public Result<Void> add(@RequestBody ExecutorInfo executorInfo) {
        executorService.addExecutor(executorInfo);
        return Result.success();
    }

    @PostMapping("/update")
    public Result<Void> update(@RequestBody ExecutorInfo executorInfo) {
        executorService.updateExecutor(executorInfo);
        return Result.success();
    }

    @PostMapping("/delete/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        executorService.deleteExecutor(id);
        return Result.success();
    }

    @PostMapping("/refresh")
    public Result<Void> refresh() {
        executorService.refreshExecutorStatus();
        return Result.success();
    }

    @GetMapping("/stats")
    public Result<Map<String, Integer>> getStats() {
        Map<String, Integer> stats = new HashMap<>();
        stats.put("online", executorService.getOnlineExecutorCount());
        stats.put("total", executorService.getTotalExecutorCount());
        return Result.success(stats);
    }
}
