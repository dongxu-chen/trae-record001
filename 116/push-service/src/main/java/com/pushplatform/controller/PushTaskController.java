package com.pushplatform.controller;

import com.pushplatform.common.core.Result;
import com.pushplatform.dto.PushTaskDTO;
import com.pushplatform.entity.PushTask;
import com.pushplatform.service.PushTaskService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/task")
public class PushTaskController {

    @Autowired
    private PushTaskService pushTaskService;

    @GetMapping("/list")
    public Result<List<PushTask>> list(@RequestParam(required = false) String channel,
                                       @RequestParam(required = false) Integer status) {
        return Result.success(pushTaskService.list(channel, status));
    }

    @GetMapping("/{id}")
    public Result<PushTask> getById(@PathVariable Long id) {
        return Result.success(pushTaskService.getById(id));
    }

    @GetMapping("/no/{taskNo}")
    public Result<PushTask> getByTaskNo(@PathVariable String taskNo) {
        return Result.success(pushTaskService.getByTaskNo(taskNo));
    }

    @PostMapping("/create")
    public Result<String> create(@Validated @RequestBody PushTaskDTO dto) {
        return Result.success(pushTaskService.create(dto));
    }

    @PostMapping("/updateStatus/{id}")
    public Result<Boolean> updateStatus(@PathVariable Long id, @RequestParam Integer status) {
        return Result.success(pushTaskService.updateStatus(id, status));
    }
}
