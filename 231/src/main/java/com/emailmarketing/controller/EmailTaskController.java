package com.emailmarketing.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.emailmarketing.common.Result;
import com.emailmarketing.entity.EmailTask;
import com.emailmarketing.service.EmailTaskService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/tasks")
public class EmailTaskController {

    @Autowired
    private EmailTaskService taskService;

    @GetMapping
    public Result<Page<EmailTask>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) Integer status) {
        return Result.success(taskService.listTasks(page, size, name, status));
    }

    @GetMapping("/{id}")
    public Result<EmailTask> getById(@PathVariable Long id) {
        return Result.success(taskService.getById(id));
    }

    @PostMapping
    public Result<Void> create(@RequestBody EmailTask task) {
        try {
            boolean success = taskService.createTask(task);
            return success ? Result.success() : Result.error("创建失败");
        } catch (RuntimeException e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/{id}/start")
    public Result<Void> start(@PathVariable Long id) {
        taskService.startTask(id);
        return Result.success();
    }

    @PostMapping("/{id}/cancel")
    public Result<Void> cancel(@PathVariable Long id) {
        boolean success = taskService.cancelTask(id);
        return success ? Result.success() : Result.error("取消失败");
    }
}
