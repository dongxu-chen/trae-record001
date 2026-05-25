package com.taskscheduler.core.service;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import com.taskscheduler.common.dto.TaskExecuteParam;
import com.taskscheduler.common.dto.TaskExecuteResult;
import com.taskscheduler.common.entity.ExecutorInfo;
import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.entity.TaskLog;
import com.taskscheduler.common.enums.ExecuteTypeEnum;
import com.taskscheduler.common.enums.ExecutorRouteStrategyEnum;
import com.taskscheduler.common.enums.TaskStatusEnum;
import com.taskscheduler.common.util.JsonUtils;
import com.taskscheduler.core.dag.DagTaskScheduler;
import com.taskscheduler.core.lock.DistributedLockManager;
import com.taskscheduler.core.mapper.TaskInfoMapper;
import com.taskscheduler.core.mapper.TaskLogMapper;
import com.taskscheduler.core.registry.ExecutorRegistry;
import com.taskscheduler.core.strategy.ExecutorRouteStrategy;
import com.taskscheduler.core.strategy.TaskShardingStrategy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.*;

@Slf4j
@Service
public class TaskScheduleService {

    @Autowired
    private TaskInfoMapper taskInfoMapper;

    @Autowired
    private TaskLogMapper taskLogMapper;

    @Autowired
    private ExecutorRegistry executorRegistry;

    @Autowired
    private TaskShardingStrategy taskShardingStrategy;

    @Autowired
    private DagTaskScheduler dagTaskScheduler;

    @Autowired
    private DistributedLockManager distributedLockManager;

    private final ExecutorService executorService = new ThreadPoolExecutor(
            10, 50, 60L, TimeUnit.SECONDS,
            new LinkedBlockingQueue<>(1000),
            new ThreadPoolExecutor.CallerRunsPolicy()
    );

    @Transactional(rollbackFor = Exception.class)
    public void triggerTask(TaskInfo taskInfo, ExecuteTypeEnum executeType, Long parentLogId) throws Exception {
        if (taskInfo.getStatus().equals(TaskStatusEnum.STOPPED.getCode())) {
            log.info("Task [{}] is stopped, skip trigger", taskInfo.getTaskName());
            return;
        }

        TaskLog taskLog = createTaskLog(taskInfo, executeType, parentLogId);

        try {
            List<ExecutorInfo> availableExecutors = executorRegistry.getAvailableExecutors();
            if (availableExecutors.isEmpty()) {
                updateTaskLogFailed(taskLog, "没有可用的执行器");
                return;
            }

            ExecutorRouteStrategy routeStrategy = ExecutorRouteStrategy.getStrategy(
                    ExecutorRouteStrategyEnum.getByCode(taskInfo.getExecutorRouteStrategy())
            );

            List<TaskExecuteParam> shardingParams = taskShardingStrategy.createShardingParams(taskInfo, taskLog.getId());

            taskLog.setTriggerCode(0);
            taskLog.setTriggerMsg("调度成功");
            taskLog.setTriggerTime(LocalDateTime.now());
            taskLogMapper.updateById(taskLog);

            for (TaskExecuteParam param : shardingParams) {
                int shardIndex = param.getShardingIndex() != null ? param.getShardingIndex() : -1;
                boolean lockAcquired = true;
                if (shardIndex >= 0) {
                    lockAcquired = distributedLockManager.tryLockShard(
                            taskInfo.getId(), taskLog.getId(), shardIndex, 3, TimeUnit.SECONDS);
                    if (!lockAcquired) {
                        log.warn("Shard lock already held, skip shard: taskId={}, logId={}, shardIndex={}",
                                taskInfo.getId(), taskLog.getId(), shardIndex);
                        continue;
                    }
                }

                ExecutorInfo executor = routeStrategy.route(availableExecutors, taskInfo.getId() + shardIndex);
                if (executor == null) {
                    log.error("No executor available for task [{}], shard [{}]", taskInfo.getTaskName(), shardIndex);
                    if (shardIndex >= 0) {
                        distributedLockManager.releaseShardLock(taskInfo.getId(), taskLog.getId(), shardIndex);
                    }
                    continue;
                }
                param.setRetryCount(0);
                submitTaskExecution(taskLog, param, executor, taskInfo);
            }

            taskInfo.setLastExecuteTime(LocalDateTime.now());
            taskInfoMapper.updateById(taskInfo);

        } catch (Exception e) {
            log.error("Trigger task [{}] failed", taskInfo.getTaskName(), e);
            updateTaskLogFailed(taskLog, "调度失败: " + e.getMessage());
            throw e;
        }
    }

    private void submitTaskExecution(TaskLog taskLog, TaskExecuteParam param,
                                     ExecutorInfo executor, TaskInfo taskInfo) {
        final int shardIndex = param.getShardingIndex() != null ? param.getShardingIndex() : -1;
        executorService.submit(() -> {
            try {
                TaskExecuteResult result = executeWithRetry(taskLog, param, executor, taskInfo);
                updateTaskLogResult(taskLog, result, shardIndex);
            } catch (Exception e) {
                log.error("Execute task [{}] shard [{}] failed", taskInfo.getTaskName(), shardIndex, e);
                TaskExecuteResult failResult = TaskExecuteResult.fail(taskLog.getId(), e.getMessage());
                failResult.setShardingIndex(shardIndex);
                updateTaskLogResult(taskLog, failResult, shardIndex);
            } finally {
                if (shardIndex >= 0) {
                    distributedLockManager.releaseShardLock(taskInfo.getId(), taskLog.getId(), shardIndex);
                }
            }
        });
    }

    private TaskExecuteResult executeWithRetry(TaskLog taskLog, TaskExecuteParam param,
                                               ExecutorInfo executor, TaskInfo taskInfo) throws Exception {
        int maxRetry = taskInfo.getMaxRetryCount() != null ? taskInfo.getMaxRetryCount() : 0;
        int retryInterval = taskInfo.getRetryInterval() != null ? taskInfo.getRetryInterval() : 60;
        int currentRetry = 0;
        Exception lastException = null;

        while (currentRetry <= maxRetry) {
            try {
                param.setRetryCount(currentRetry);
                TaskExecuteResult result = executeTaskWithTimeout(param, executor, taskInfo.getTaskTimeout());
                if (result.getExecuteCode() == 0) {
                    return result;
                }
                lastException = new RuntimeException(result.getExecuteMsg());
            } catch (TimeoutException e) {
                lastException = new RuntimeException("任务执行超时(" + taskInfo.getTaskTimeout() + "秒)");
            } catch (Exception e) {
                lastException = e;
            }

            currentRetry++;
            if (currentRetry <= maxRetry) {
                log.warn("Task [{}] shard [{}] execute failed, retry {}/{} after {}s",
                        taskInfo.getTaskName(), param.getShardingIndex(), currentRetry, maxRetry, retryInterval);
                Thread.sleep(retryInterval * 1000L);
            }
        }

        throw lastException != null ? lastException : new RuntimeException("任务执行失败");
    }

    private TaskExecuteResult executeTaskWithTimeout(TaskExecuteParam param, ExecutorInfo executor, Integer timeout) throws Exception {
        int timeoutSeconds = timeout != null && timeout > 0 ? timeout : 300;

        Future<TaskExecuteResult> future = executorService.submit(() -> {
            String url = "http://" + executor.getExecutorAddress() + "/api/executor/run";
            String body = JsonUtils.toJsonString(param);

            try {
                HttpResponse response = HttpRequest.post(url)
                        .body(body)
                        .timeout(timeoutSeconds * 1000)
                        .execute();

                String resultStr = response.body();
                return JsonUtils.parseObject(resultStr, TaskExecuteResult.class);
            } catch (Exception e) {
                log.error("Call executor failed, url: {}, param: {}", url, param, e);
                TaskExecuteResult result = new TaskExecuteResult();
                result.setLogId(param.getLogId());
                result.setExecuteCode(500);
                result.setExecuteMsg("调用执行器失败: " + e.getMessage());
                return result;
            }
        });

        try {
            return future.get(timeoutSeconds + 5, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            future.cancel(true);
            throw new TimeoutException("任务执行超时");
        } catch (ExecutionException e) {
            throw (Exception) e.getCause();
        }
    }

    private TaskLog createTaskLog(TaskInfo taskInfo, ExecuteTypeEnum executeType, Long parentLogId) {
        TaskLog taskLog = new TaskLog();
        taskLog.setTaskId(taskInfo.getId());
        taskLog.setTaskName(taskInfo.getTaskName());
        taskLog.setTaskGroup(taskInfo.getTaskGroup());
        taskLog.setHandler(taskInfo.getHandler());
        taskLog.setParams(taskInfo.getParams());
        taskLog.setExecuteType(executeType.getCode());
        taskLog.setTriggerCode(500);
        taskLog.setTriggerMsg("调度中");
        taskLog.setShardingTotal(taskInfo.getShardingTotal());
        taskLog.setRetryCount(0);
        taskLog.setParentLogId(parentLogId);
        taskLog.setCreateTime(LocalDateTime.now());
        taskLog.setUpdateTime(LocalDateTime.now());
        taskLogMapper.insert(taskLog);
        return taskLog;
    }

    private void updateTaskLogFailed(TaskLog taskLog, String msg) {
        taskLog.setTriggerCode(500);
        taskLog.setTriggerMsg(msg);
        taskLog.setExecuteCode(500);
        taskLog.setExecuteMsg(msg);
        taskLog.setExecuteStartTime(LocalDateTime.now());
        taskLog.setExecuteEndTime(LocalDateTime.now());
        taskLog.setUpdateTime(LocalDateTime.now());
        taskLogMapper.updateById(taskLog);
    }

    private synchronized void updateTaskLogResult(TaskLog taskLog, TaskExecuteResult result, Integer shardingIndex) {
        TaskLog existLog = taskLogMapper.selectById(taskLog.getId());
        if (existLog == null) {
            return;
        }

        if (shardingIndex != null && shardingIndex >= 0) {
            existLog.setShardingIndex(shardingIndex);
        }

        if (existLog.getExecuteCode() == null || existLog.getExecuteCode() != 0) {
            existLog.setExecuteCode(result.getExecuteCode());
            existLog.setExecuteMsg(result.getExecuteMsg());
            existLog.setExecuteStartTime(result.getExecuteStartTime());
            existLog.setExecuteEndTime(result.getExecuteEndTime());
        } else if (result.getExecuteCode() != null && result.getExecuteCode() != 0) {
            existLog.setExecuteMsg((existLog.getExecuteMsg() != null ? existLog.getExecuteMsg() + "; " : "")
                    + "分片[" + shardingIndex + "]失败: " + result.getExecuteMsg());
        }

        existLog.setUpdateTime(LocalDateTime.now());
        taskLogMapper.updateById(existLog);
    }

    @Scheduled(fixedDelay = 10000)
    public void scanDagTasks() {
        try {
            List<TaskInfo> readyTasks = dagTaskScheduler.getDagReadyTasks();
            for (TaskInfo task : readyTasks) {
                try {
                    triggerTask(task, ExecuteTypeEnum.NORMAL, null);
                } catch (Exception e) {
                    log.error("Trigger DAG task [{}] failed", task.getTaskName(), e);
                }
            }
        } catch (Exception e) {
            log.error("Scan DAG tasks failed", e);
        }
    }

    @Scheduled(fixedDelay = 30000)
    public void checkTimeoutTasks() {
        try {
            LocalDateTime thirtyMinutesAgo = LocalDateTime.now().minusMinutes(30);
            List<TaskLog> timeoutLogs = taskLogMapper.selectList(
                    new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TaskLog>()
                            .isNull("execute_code")
                            .isNotNull("execute_start_time")
                            .lt("execute_start_time", thirtyMinutesAgo)
            );

            for (TaskLog log : timeoutLogs) {
                log.setExecuteCode(504);
                log.setExecuteMsg("任务执行超时(超过30分钟未完成)");
                log.setExecuteEndTime(LocalDateTime.now());
                log.setUpdateTime(LocalDateTime.now());
                taskLogMapper.updateById(log);
            }
        } catch (Exception e) {
            log.error("Check timeout tasks failed", e);
        }
    }
}
