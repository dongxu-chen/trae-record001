package com.taskscheduler.admin.controller;

import com.taskscheduler.common.dto.PageResult;
import com.taskscheduler.common.dto.Result;
import com.taskscheduler.common.dto.TaskLogQueryDTO;
import com.taskscheduler.common.entity.TaskLog;
import com.taskscheduler.core.service.TaskLogService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/task-log")
public class TaskLogController {

    @Autowired
    private TaskLogService taskLogService;

    @PostMapping("/list")
    public Result<PageResult<TaskLog>> list(@RequestBody TaskLogQueryDTO queryDTO) {
        return Result.success(taskLogService.queryTaskLogs(queryDTO));
    }

    @GetMapping("/{id}")
    public Result<TaskLog> getById(@PathVariable Long id) {
        return Result.success(taskLogService.getTaskLogById(id));
    }

    @GetMapping("/task/{taskId}")
    public Result<List<TaskLog>> getByTaskId(@PathVariable Long taskId,
                                              @RequestParam(defaultValue = "20") int limit) {
        return Result.success(taskLogService.getTaskLogsByTaskId(taskId, limit));
    }

    @PostMapping("/clear")
    public Result<Void> clearLogs(@RequestParam(required = false) Integer days) {
        taskLogService.clearLogs(days);
        return Result.success();
    }
}
