package com.taskscheduler.executor.controller;

import com.taskscheduler.common.dto.Result;
import com.taskscheduler.common.dto.TaskExecuteParam;
import com.taskscheduler.common.dto.TaskExecuteResult;
import com.taskscheduler.common.handler.ITaskHandler;
import com.taskscheduler.executor.manager.TaskHandlerManager;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.concurrent.*;

@Slf4j
@RestController
@RequestMapping("/api/executor")
public class ExecutorController {

    @Autowired
    private TaskHandlerManager taskHandlerManager;

    private final ExecutorService executorService = new ThreadPoolExecutor(
            10, 100, 60L, TimeUnit.SECONDS,
            new LinkedBlockingQueue<>(1000),
            new ThreadPoolExecutor.CallerRunsPolicy()
    );

    @PostMapping("/run")
    public Result<TaskExecuteResult> run(@RequestBody TaskExecuteParam param) {
        log.info("Receive task execute request, taskId: {}, logId: {}, handler: {}, shard: {}/{}",
                param.getTaskId(), param.getLogId(), param.getHandler(),
                param.getShardingIndex(), param.getShardingTotal());

        TaskExecuteResult result = new TaskExecuteResult();
        result.setLogId(param.getLogId());
        result.setShardingIndex(param.getShardingIndex());
        result.setExecuteStartTime(LocalDateTime.now());

        try {
            ITaskHandler handler = taskHandlerManager.getHandler(param.getHandler());
            if (handler == null) {
                result.setExecuteCode(500);
                result.setExecuteMsg("任务处理器不存在: " + param.getHandler());
                result.setExecuteEndTime(LocalDateTime.now());
                return Result.success(result);
            }

            int timeout = param.getTimeout() != null && param.getTimeout() > 0 ? param.getTimeout() : 300;

            Future<TaskExecuteResult> future = executorService.submit(() -> {
                try {
                    return handler.execute(param);
                } catch (Exception e) {
                    log.error("Task execute failed, taskId: {}, handler: {}", param.getTaskId(), param.getHandler(), e);
                    TaskExecuteResult failResult = new TaskExecuteResult();
                    failResult.setLogId(param.getLogId());
                    failResult.setShardingIndex(param.getShardingIndex());
                    failResult.setExecuteCode(500);
                    failResult.setExecuteMsg("执行异常: " + e.getMessage());
                    failResult.setExecuteStartTime(LocalDateTime.now());
                    failResult.setExecuteEndTime(LocalDateTime.now());
                    return failResult;
                }
            });

            TaskExecuteResult executeResult = future.get(timeout, TimeUnit.SECONDS);
            if (executeResult.getExecuteStartTime() == null) {
                executeResult.setExecuteStartTime(result.getExecuteStartTime());
            }
            if (executeResult.getExecuteEndTime() == null) {
                executeResult.setExecuteEndTime(LocalDateTime.now());
            }
            executeResult.setLogId(param.getLogId());
            executeResult.setShardingIndex(param.getShardingIndex());

            log.info("Task execute completed, taskId: {}, logId: {}, code: {}",
                    param.getTaskId(), param.getLogId(), executeResult.getExecuteCode());

            return Result.success(executeResult);

        } catch (TimeoutException e) {
            log.error("Task execute timeout, taskId: {}, logId: {}, timeout: {}s",
                    param.getTaskId(), param.getLogId(), param.getTimeout());
            result.setExecuteCode(504);
            result.setExecuteMsg("任务执行超时(" + param.getTimeout() + "秒)");
            result.setExecuteEndTime(LocalDateTime.now());
            return Result.success(result);
        } catch (Exception e) {
            log.error("Task execute error, taskId: {}, logId: {}", param.getTaskId(), param.getLogId(), e);
            result.setExecuteCode(500);
            result.setExecuteMsg("执行器异常: " + e.getMessage());
            result.setExecuteEndTime(LocalDateTime.now());
            return Result.success(result);
        }
    }

    @GetMapping("/ping")
    public Result<String> ping() {
        return Result.success("pong");
    }

    @GetMapping("/heartbeat")
    public Result<String> heartbeat() {
        return Result.success("ok");
    }
}
