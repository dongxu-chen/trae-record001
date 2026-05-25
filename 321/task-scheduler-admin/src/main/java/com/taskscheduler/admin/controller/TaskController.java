package com.taskscheduler.admin.controller;

import com.taskscheduler.common.dto.PageResult;
import com.taskscheduler.common.dto.Result;
import com.taskscheduler.common.dto.TaskQueryDTO;
import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.enums.TaskTypeEnum;
import com.taskscheduler.common.util.CronUtils;
import com.taskscheduler.core.dag.DagTaskScheduler;
import com.taskscheduler.core.service.TaskService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/task")
public class TaskController {

    @Autowired
    private TaskService taskService;

    @Autowired
    private DagTaskScheduler dagTaskScheduler;

    @Autowired
    private TaskPredictionService taskPredictionService;

    @PostMapping("/list")
    public Result<PageResult<TaskInfo>> list(@RequestBody TaskQueryDTO queryDTO) {
        return Result.success(taskService.queryTasks(queryDTO));
    }

    @GetMapping("/{id}")
    public Result<TaskInfo> getById(@PathVariable Long id) {
        return Result.success(taskService.getTaskById(id));
    }

    @PostMapping("/add")
    public Result<Void> add(@RequestBody TaskInfo taskInfo) {
        try {
            taskService.addTask(taskInfo);
            if (TaskTypeEnum.DAG.getCode().equals(taskInfo.getTaskType())) {
                dagTaskScheduler.invalidateCache();
            }
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/update")
    public Result<Void> update(@RequestBody TaskInfo taskInfo) {
        try {
            taskService.updateTask(taskInfo);
            dagTaskScheduler.invalidateCache();
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/delete/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        try {
            taskService.deleteTask(id);
            dagTaskScheduler.invalidateCache();
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/start/{id}")
    public Result<Void> start(@PathVariable Long id) {
        try {
            taskService.startTask(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/stop/{id}")
    public Result<Void> stop(@PathVariable Long id) {
        try {
            taskService.stopTask(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/trigger/{id}")
    public Result<Void> trigger(@PathVariable Long id) {
        try {
            taskService.triggerTask(id);
            return Result.success();
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/validate-cron")
    public Result<Boolean> validateCron(@RequestParam String cron) {
        return Result.success(CronUtils.isValid(cron));
    }

    @GetMapping("/next-executions")
    public Result<List<String>> getNextExecutions(@RequestParam String cron, @RequestParam(defaultValue = "5") int count) {
        try {
            return Result.success(CronUtils.getNextExecutionTimes(cron, count));
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/prediction/{taskId}")
    public Result<com.taskscheduler.common.dto.TaskPredictionDTO> getPrediction(@PathVariable Long taskId) {
        try {
            return Result.success(taskPredictionService.predictTaskDuration(taskId));
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/prediction/invalidate/{taskId}")
    public Result<Void> invalidatePredictionCache(@PathVariable Long taskId) {
        taskPredictionService.invalidateCache(taskId);
        return Result.success();
    }
}
