package com.taskscheduler.core.service;

import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.enums.ExecuteTypeEnum;
import com.taskscheduler.common.enums.TaskPriorityEnum;
import com.taskscheduler.core.queue.PriorityTaskQueue;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.concurrent.*;

@Slf4j
@Service
public class PriorityTaskSchedulerService {

    @Autowired
    private PriorityTaskQueue priorityTaskQueue;

    @Autowired
    private TaskScheduleService taskScheduleService;

    @Autowired
    private com.taskscheduler.core.mapper.TaskInfoMapper taskInfoMapper;

    private final ExecutorService schedulerExecutor = new ThreadPoolExecutor(
            5, 20, 60L, TimeUnit.SECONDS,
            new LinkedBlockingQueue<>(100),
            new ThreadPoolExecutor.CallerRunsPolicy()
    );

    private volatile boolean running = true;

    private final ConcurrentHashMap<Long, Future<?>> runningFutures = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        for (int i = 0; i < 5; i++) {
            schedulerExecutor.submit(this::runSchedulerLoop);
        }
        log.info("PriorityTaskSchedulerService started with 5 worker threads");
    }

    @PreDestroy
    public void destroy() {
        running = false;
        priorityTaskQueue.clear();
        for (Future<?> future : runningFutures.values()) {
            future.cancel(true);
        }
        runningFutures.clear();
        schedulerExecutor.shutdownNow();
        log.info("PriorityTaskSchedulerService stopped");
    }

    private void runSchedulerLoop() {
        while (running && !Thread.currentThread().isInterrupted()) {
            try {
                PriorityTaskQueue.PriorityTask task = priorityTaskQueue.poll(5, TimeUnit.SECONDS);
                if (task == null) {
                    continue;
                }

                log.info("Dequeued priority task: [{}] priority={}, queue size={}",
                        task.getTaskInfo().getTaskName(), task.getPriority(), priorityTaskQueue.size());

                executePriorityTask(task);

            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                log.error("Scheduler loop error", e);
            }
        }
    }

    private void executePriorityTask(PriorityTaskQueue.PriorityTask priorityTask) {
        TaskInfo taskInfo = priorityTask.getTaskInfo();
        int priority = priorityTask.getPriority();

        priorityTaskQueue.incrementRunning(priority);

        Future<?> future = schedulerExecutor.submit(() -> {
            try {
                log.info("Executing priority task [{}] with priority={}", taskInfo.getTaskName(), priority);

                ExecuteTypeEnum executeType = "MANUAL".equals(priorityTask.getExecuteType())
                        ? ExecuteTypeEnum.MANUAL
                        : ExecuteTypeEnum.NORMAL;

                taskScheduleService.triggerTask(taskInfo, executeType, priorityTask.getParentLogId());

                log.info("Priority task [{}] execution completed, priority={}", taskInfo.getTaskName(), priority);

            } catch (Exception e) {
                log.error("Priority task [{}] execution failed", taskInfo.getTaskName(), e);
            } finally {
                priorityTaskQueue.decrementRunning(priority);
                runningFutures.remove(taskInfo.getId());
            }
        });

        runningFutures.put(taskInfo.getId(), future);
    }

    public boolean submitTask(Long taskId, Long parentLogId, String executeType) {
        TaskInfo taskInfo = taskInfoMapper.selectById(taskId);
        if (taskInfo == null) {
            log.error("Task not found: {}", taskId);
            return false;
        }

        int priority = taskInfo.getPriority() != null ? taskInfo.getPriority() : 5;
        if (!TaskPriorityEnum.isValid(priority)) {
            log.warn("Invalid priority {} for task {}, using default 5", priority, taskInfo.getTaskName());
            taskInfo.setPriority(5);
        }

        return priorityTaskQueue.submit(taskInfo, null, parentLogId, executeType);
    }

    public boolean submitTask(TaskInfo taskInfo, Long logId, Long parentLogId, String executeType) {
        int priority = taskInfo.getPriority() != null ? taskInfo.getPriority() : 5;
        if (!TaskPriorityEnum.isValid(priority)) {
            log.warn("Invalid priority {} for task {}, using default 5", priority, taskInfo.getTaskName());
            taskInfo.setPriority(5);
        }

        return priorityTaskQueue.submit(taskInfo, logId, parentLogId, executeType);
    }

    public int getQueueSize() {
        return priorityTaskQueue.size();
    }

    public int getRunningCount() {
        return priorityTaskQueue.getTotalRunning();
    }

    public boolean removeQueuedTask(Long taskId) {
        return priorityTaskQueue.removeTask(taskId);
    }

    public void clearQueue() {
        priorityTaskQueue.clear();
    }
}
