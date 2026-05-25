package com.taskscheduler.core.queue;

import com.taskscheduler.common.entity.TaskInfo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Comparator;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Component
public class PriorityTaskQueue {

    private static final int DEFAULT_QUEUE_CAPACITY = 10000;
    private static final int DEFAULT_PREEMPTION_THRESHOLD = 3;

    private final PriorityBlockingQueue<PriorityTask> taskQueue = new PriorityBlockingQueue<>(
            DEFAULT_QUEUE_CAPACITY,
            Comparator.comparingInt(PriorityTask::getPriority)
                    .thenComparingLong(PriorityTask::getCreateTime)
    );

    private final ConcurrentHashMap<Long, Long> runningTaskCount = new ConcurrentHashMap<>();
    private final AtomicInteger totalRunningTasks = new AtomicInteger(0);

    public static class PriorityTask {
        private final TaskInfo taskInfo;
        private final Long logId;
        private final Long parentLogId;
        private final Integer priority;
        private final long createTime;
        private final String executeType;

        public PriorityTask(TaskInfo taskInfo, Long logId, Long parentLogId, String executeType) {
            this.taskInfo = taskInfo;
            this.logId = logId;
            this.parentLogId = parentLogId;
            this.priority = taskInfo.getPriority() != null ? taskInfo.getPriority() : 5;
            this.createTime = System.currentTimeMillis();
            this.executeType = executeType;
        }

        public int getPriority() {
            return priority;
        }

        public long getCreateTime() {
            return createTime;
        }

        public TaskInfo getTaskInfo() {
            return taskInfo;
        }

        public Long getLogId() {
            return logId;
        }

        public Long getParentLogId() {
            return parentLogId;
        }

        public String getExecuteType() {
            return executeType;
        }
    }

    public boolean submit(TaskInfo taskInfo, Long logId, Long parentLogId, String executeType) {
        int priority = taskInfo.getPriority() != null ? taskInfo.getPriority() : 5;

        boolean canPreempt = checkAndPreempt(priority);

        if (taskQueue.size() >= DEFAULT_QUEUE_CAPACITY) {
            if (priority <= DEFAULT_PREEMPTION_THRESHOLD) {
                PriorityTask lowestPriorityTask = taskQueue.stream()
                        .filter(t -> t.getPriority() > priority)
                        .max(Comparator.comparingInt(PriorityTask::getPriority))
                        .orElse(null);

                if (lowestPriorityTask != null && taskQueue.remove(lowestPriorityTask)) {
                    log.warn("Queue full, high priority task [{}] preempted, removed low priority task: {}",
                            taskInfo.getTaskName(), lowestPriorityTask.getTaskInfo().getTaskName());
                } else {
                    log.warn("Queue full and no low priority task to preempt, reject task: {}", taskInfo.getTaskName());
                    return false;
                }
            } else {
                log.warn("Queue full, reject low priority task: {}", taskInfo.getTaskName());
                return false;
            }
        }

        PriorityTask priorityTask = new PriorityTask(taskInfo, logId, parentLogId, executeType);
        boolean offered = taskQueue.offer(priorityTask);
        if (offered) {
            log.debug("Task [{}] submitted to queue with priority {}, queue size: {}",
                    taskInfo.getTaskName(), priority, taskQueue.size());
        }
        return offered;
    }

    private boolean checkAndPreempt(int priority) {
        if (priority > DEFAULT_PREEMPTION_THRESHOLD) {
            return false;
        }

        int maxConcurrency = 50;
        int currentRunning = totalRunningTasks.get();

        if (currentRunning >= maxConcurrency) {
            long lowPriorityRunning = runningTaskCount.entrySet().stream()
                    .filter(e -> {
                        int p = (int) (long) e.getKey();
                        return p > priority && e.getValue() > 0;
                    })
                    .mapToLong(Map.Entry::getValue)
                    .sum();

            if (lowPriorityRunning > 0) {
                log.info("High priority task (prio={}) can preempt {} low priority running slots",
                        priority, lowPriorityRunning);
                return true;
            }
        }

        return false;
    }

    public PriorityTask poll(long timeout, TimeUnit unit) throws InterruptedException {
        return taskQueue.poll(timeout, unit);
    }

    public PriorityTask poll() {
        return taskQueue.poll();
    }

    public int size() {
        return taskQueue.size();
    }

    public void incrementRunning(int priority) {
        runningTaskCount.merge((long) priority, 1L, Long::sum);
        totalRunningTasks.incrementAndGet();
    }

    public void decrementRunning(int priority) {
        runningTaskCount.merge((long) priority, -1L, Long::sum);
        totalRunningTasks.decrementAndGet();
    }

    public int getTotalRunning() {
        return totalRunningTasks.get();
    }

    public void clear() {
        taskQueue.clear();
    }

    public boolean removeTask(Long taskId) {
        return taskQueue.removeIf(t -> t.getTaskInfo().getId().equals(taskId));
    }
}
