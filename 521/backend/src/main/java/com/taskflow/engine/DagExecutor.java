package com.taskflow.engine;

import com.taskflow.dto.TaskDto;
import com.taskflow.model.Task;
import com.taskflow.model.TaskExecution;
import com.taskflow.model.WorkflowExecution;
import com.taskflow.repository.TaskExecutionRepository;
import com.taskflow.repository.TaskRepository;
import com.taskflow.repository.WorkflowExecutionRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;
import java.util.stream.Collectors;

@Slf4j
public class DagExecutor {

    private final TaskRepository taskRepository;
    private final TaskExecutionRepository taskExecutionRepository;
    private final WorkflowExecutionRepository workflowExecutionRepository;
    private final ThreadPoolTaskExecutor taskExecutor;
    private final ObjectMapper objectMapper;
    private final Consumer<List<String>> dataProductCallback;

    public DagExecutor(TaskRepository taskRepository,
                       TaskExecutionRepository taskExecutionRepository,
                       WorkflowExecutionRepository workflowExecutionRepository,
                       ThreadPoolTaskExecutor taskExecutor,
                       ObjectMapper objectMapper,
                       Consumer<List<String>> dataProductCallback) {
        this.taskRepository = taskRepository;
        this.taskExecutionRepository = taskExecutionRepository;
        this.workflowExecutionRepository = workflowExecutionRepository;
        this.taskExecutor = taskExecutor;
        this.objectMapper = objectMapper;
        this.dataProductCallback = dataProductCallback;
    }

    public void execute(WorkflowExecution workflowExecution) {
        Long workflowId = workflowExecution.getWorkflowId();
        List<Task> allTasks = taskRepository.findByWorkflowId(workflowId);

        if (allTasks.isEmpty()) {
            workflowExecution.setStatus("SUCCESS");
            workflowExecution.setStartedAt(LocalDateTime.now());
            workflowExecution.setFinishedAt(LocalDateTime.now());
            workflowExecutionRepository.save(workflowExecution);
            return;
        }

        workflowExecution.setStatus("RUNNING");
        workflowExecution.setStartedAt(LocalDateTime.now());
        workflowExecutionRepository.save(workflowExecution);

        DagGraph dagGraph = new DagGraph(allTasks);
        ConcurrentHashMap<String, TaskExecution> executionMap = new ConcurrentHashMap<>();
        ConcurrentHashMap<String, Object> context = new ConcurrentHashMap<>();
        CountDownLatch latch = new CountDownLatch(allTasks.size());
        AtomicBoolean workflowFailed = new AtomicBoolean(false);

        Set<String> resolved = ConcurrentHashMap.newKeySet();
        PriorityBlockingQueue<ReadyTask> readyQueue = new PriorityBlockingQueue<>(
            1000,
            Comparator.comparingInt((ReadyTask rt) -> -rt.priority)
                      .thenComparingLong(rt -> rt.createTime)
        );

        for (String root : dagGraph.getRootKeys()) {
            Task rootTask = dagGraph.getTask(root);
            if (rootTask != null) {
                readyQueue.add(new ReadyTask(root, rootTask.getTaskPriority()));
            }
        }

        while (!readyQueue.isEmpty() || latch.getCount() > 0) {
            if (workflowFailed.get()) {
                break;
            }

            ReadyTask ready = readyQueue.poll();
            if (ready == null) {
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
                continue;
            }

            String taskKey = ready.taskKey;
            if (resolved.contains(taskKey)) {
                latch.countDown();
                continue;
            }

            Task task = dagGraph.getTask(taskKey);
            if (task == null) {
                latch.countDown();
                continue;
            }

            TaskExecution te = resolveTaskExecution(workflowExecution.getId(), task);
            executionMap.put(taskKey, te);
            resolved.add(taskKey);

            taskExecutor.submit(() -> {
                try {
                    executeTaskWithSmartRetry(task, te, context);

                    if ("SUCCESS".equals(te.getStatus())) {
                        List<String> dataProducts = parseJsonList(task.getDataProducts());
                        if (!dataProducts.isEmpty() && dataProductCallback != null) {
                            try {
                                dataProductCallback.accept(dataProducts);
                                log.info("Data lineage triggered for products: {}", dataProducts);
                            } catch (Exception e) {
                                log.error("Failed to trigger data lineage callback", e);
                            }
                        }

                        SubGraph subGraph = dagGraph.resolveSubGraph(taskKey);
                        for (String downKey : subGraph.getNewlyReadyKeys()) {
                            if (!resolved.contains(downKey)) {
                                Task downTask = dagGraph.getTask(downKey);
                                if (downTask != null) {
                                    readyQueue.add(new ReadyTask(downKey, downTask.getTaskPriority()));
                                    log.info("Subgraph incremental resolve: task [{}] completed, downstream [{}] (P{}) now ready",
                                            taskKey, downKey, downTask.getTaskPriority());
                                }
                            }
                        }
                    } else {
                        workflowFailed.set(true);
                    }
                } finally {
                    latch.countDown();
                }
            });
        }

        try {
            latch.await(1, TimeUnit.HOURS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        boolean allSuccess = executionMap.values().stream()
                .allMatch(te -> "SUCCESS".equals(te.getStatus()));

        workflowExecution.setStatus(allSuccess ? "SUCCESS" : "FAILED");
        workflowExecution.setFinishedAt(LocalDateTime.now());
        workflowExecutionRepository.save(workflowExecution);
    }

    private TaskExecution resolveTaskExecution(Long workflowExecutionId, Task task) {
        TaskExecution te = new TaskExecution();
        te.setWorkflowExecutionId(workflowExecutionId);
        te.setTaskId(task.getId());
        te.setTaskKey(task.getTaskKey());
        te.setStatus("PENDING");
        te.setAttempt(1);
        taskExecutionRepository.save(te);
        return te;
    }

    private void executeTaskWithSmartRetry(Task task, TaskExecution te,
                                           ConcurrentHashMap<String, Object> context) {
        int maxRetry = task.getRetryCount();
        int baseInterval = task.getRetryInterval();
        String retryStrategy = task.getRetryStrategy();
        int timeoutSeconds = task.getTimeoutSeconds();
        int attempt = 0;

        while (attempt <= maxRetry) {
            attempt++;
            te.setAttempt(attempt);
            te.setStatus("RUNNING");
            te.setStartedAt(LocalDateTime.now());
            te.setWorkerNode("node-1");
            taskExecutionRepository.save(te);

            try {
                ExecutorService singleThreadExecutor = Executors.newSingleThreadExecutor();
                Future<String> future = singleThreadExecutor.submit(() ->
                        simulateTaskExecution(task, context));

                String result;
                try {
                    result = future.get(timeoutSeconds, TimeUnit.SECONDS);
                } catch (TimeoutException e) {
                    future.cancel(true);
                    singleThreadExecutor.shutdownNow();
                    throw new TaskFailedException("TIMEOUT",
                            "Task timed out after " + timeoutSeconds + " seconds");
                } finally {
                    singleThreadExecutor.shutdownNow();
                }

                te.setStatus("SUCCESS");
                te.setLogText(result);
                te.setFinishedAt(LocalDateTime.now());
                te.setDurationMs(Duration.between(te.getStartedAt(), te.getFinishedAt()).toMillis());
                taskExecutionRepository.save(te);
                context.put(task.getTaskKey(), result);
                return;

            } catch (Exception e) {
                TaskDto.FailureType failureType = classifyFailure(e);
                String errorMsg = "[" + failureType + "] " + e.getMessage();
                te.setErrorMessage(errorMsg);
                te.setLogText("Attempt " + attempt + " failed: " + errorMsg);

                boolean shouldRetry = shouldRetry(failureType, retryStrategy, attempt, maxRetry);

                if (shouldRetry && attempt <= maxRetry) {
                    long waitMs = calculateRetryDelay(retryStrategy, baseInterval, attempt);
                    log.warn("Task {} attempt {} failed (type: {}), retrying in {}ms...",
                            task.getTaskKey(), attempt, failureType, waitMs);
                    try {
                        Thread.sleep(waitMs);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                } else {
                    te.setStatus("FAILED");
                    te.setFinishedAt(LocalDateTime.now());
                    te.setDurationMs(Duration.between(te.getStartedAt(), te.getFinishedAt()).toMillis());
                    taskExecutionRepository.save(te);
                    log.error("Task {} failed after {} attempts, final failure type: {}",
                            task.getTaskKey(), attempt, failureType);
                    break;
                }
            }
        }
    }

    private TaskDto.FailureType classifyFailure(Exception e) {
        String msg = e.getMessage() != null ? e.getMessage().toLowerCase() : "";
        String className = e.getClass().getSimpleName().toLowerCase();

        if (e instanceof TaskFailedException) {
            return TaskDto.FailureType.valueOf(((TaskFailedException) e).getFailureType());
        }

        if (msg.contains("timeout") || msg.contains("timed out") || className.contains("timeoutexception")) {
            return TaskDto.FailureType.TIMEOUT;
        }
        if (msg.contains("connection") || msg.contains("socket") || msg.contains("network")
                || msg.contains(" refused") || msg.contains("unreachable")) {
            return TaskDto.FailureType.NETWORK_ERROR;
        }
        if (msg.contains("oom") || msg.contains("out of memory") || msg.contains("no space")
                || msg.contains("resource") || msg.contains("too many")) {
            return TaskDto.FailureType.RESOURCE_ERROR;
        }
        if (msg.contains("business") || msg.contains("invalid") || msg.contains("illegal")
                || msg.contains("not found") || msg.contains("permission")) {
            return TaskDto.FailureType.BUSINESS_ERROR;
        }

        return TaskDto.FailureType.UNKNOWN;
    }

    private boolean shouldRetry(TaskDto.FailureType failureType, String retryStrategy,
                                int attempt, int maxRetry) {
        if (TaskDto.RetryStrategy.NONE.name().equals(retryStrategy)) {
            return false;
        }

        switch (failureType) {
            case NETWORK_ERROR:
            case TIMEOUT:
            case RESOURCE_ERROR:
                return true;
            case BUSINESS_ERROR:
                return attempt <= Math.min(2, maxRetry);
            case UNKNOWN:
                return attempt <= Math.min(1, maxRetry);
            default:
                return false;
        }
    }

    private long calculateRetryDelay(String strategy, int baseInterval, int attempt) {
        TaskDto.RetryStrategy s;
        try {
            s = TaskDto.RetryStrategy.valueOf(strategy);
        } catch (Exception e) {
            s = TaskDto.RetryStrategy.FIXED;
        }

        switch (s) {
            case EXPONENTIAL:
                return (long) Math.min(baseInterval * 1000 * Math.pow(2, attempt - 1), 5 * 60 * 1000);
            case LINEAR:
                return (long) baseInterval * 1000 * attempt;
            case FIXED:
            default:
                return (long) baseInterval * 1000;
        }
    }

    private String simulateTaskExecution(Task task, ConcurrentHashMap<String, Object> context) {
        try {
            String taskType = task.getTaskType();
            switch (taskType) {
                case "SHELL":
                    Thread.sleep(1000 + (long)(Math.random() * 2000));
                    return "Shell task " + task.getTaskKey() + " executed successfully";
                case "HTTP":
                    Thread.sleep(500 + (long)(Math.random() * 1000));
                    return "HTTP task " + task.getTaskKey() + " received response 200";
                case "PYTHON":
                    Thread.sleep(1500 + (long)(Math.random() * 3000));
                    return "Python task " + task.getTaskKey() + " completed";
                case "DATA_SYNC":
                    Thread.sleep(2000 + (long)(Math.random() * 3000));
                    return "Data sync task " + task.getTaskKey() + " synced 1000 records";
                case "EMAIL":
                    Thread.sleep(300 + (long)(Math.random() * 500));
                    return "Email task " + task.getTaskKey() + " sent successfully";
                default:
                    Thread.sleep(1000);
                    return "Task " + task.getTaskKey() + " of type " + taskType + " executed";
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return "INTERRUPTED";
        }
    }

    private List<String> parseJsonList(String json) {
        if (json == null || json.trim().isEmpty() || "null".equals(json)) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (Exception e) {
            return Collections.emptyList();
        }
    }

    public static class TaskFailedException extends RuntimeException {
        private final String failureType;
        public TaskFailedException(String failureType, String message) {
            super(message);
            this.failureType = failureType;
        }
        public String getFailureType() { return failureType; }
    }

    public static class ReadyTask {
        final String taskKey;
        final int priority;
        final long createTime;
        public ReadyTask(String taskKey, int priority) {
            this.taskKey = taskKey;
            this.priority = priority;
            this.createTime = System.currentTimeMillis();
        }
    }

    public class DagGraph {

        private final Map<String, Task> taskMap;
        private final Map<String, Set<String>> upstreamMap;
        private final Map<String, Set<String>> downstreamMap;
        private final Map<String, Integer> pendingUpstreamCount;
        private final Set<String> completedKeys;

        public DagGraph(List<Task> tasks) {
            this.taskMap = new HashMap<>();
            this.upstreamMap = new HashMap<>();
            this.downstreamMap = new HashMap<>();
            this.pendingUpstreamCount = new ConcurrentHashMap<>();
            this.completedKeys = ConcurrentHashMap.newKeySet();

            for (Task task : tasks) {
                taskMap.put(task.getTaskKey(), task);
                upstreamMap.putIfAbsent(task.getTaskKey(), new HashSet<>());
                downstreamMap.putIfAbsent(task.getTaskKey(), new HashSet<>());

                List<String> ups = parseJsonList(task.getUpstreamKeys());
                for (String upKey : ups) {
                    upstreamMap.get(task.getTaskKey()).add(upKey);
                    downstreamMap.computeIfAbsent(upKey, k -> new HashSet<>()).add(task.getTaskKey());
                }
                pendingUpstreamCount.put(task.getTaskKey(), ups.size());
            }
        }

        public List<String> getRootKeys() {
            return taskMap.keySet().stream()
                    .filter(k -> pendingUpstreamCount.getOrDefault(k, 0) == 0)
                    .collect(Collectors.toList());
        }

        public Task getTask(String taskKey) {
            return taskMap.get(taskKey);
        }

        public SubGraph resolveSubGraph(String completedTaskKey) {
            completedKeys.add(completedTaskKey);
            List<String> newlyReady = new ArrayList<>();

            Set<String> downstream = downstreamMap.getOrDefault(completedTaskKey, Collections.emptySet());
            for (String downKey : downstream) {
                int remaining = pendingUpstreamCount.merge(downKey, -1, Integer::sum);
                if (remaining <= 0) {
                    boolean allUpstreamDone = upstreamMap.getOrDefault(downKey, Collections.emptySet())
                            .stream().allMatch(completedKeys::contains);
                    if (allUpstreamDone) {
                        newlyReady.add(downKey);
                    }
                }
            }

            return new SubGraph(completedTaskKey, newlyReady);
        }
    }

    public static class SubGraph {
        private final String completedKey;
        private final List<String> newlyReadyKeys;

        public SubGraph(String completedKey, List<String> newlyReadyKeys) {
            this.completedKey = completedKey;
            this.newlyReadyKeys = newlyReadyKeys;
        }

        public String getCompletedKey() { return completedKey; }
        public List<String> getNewlyReadyKeys() { return newlyReadyKeys; }
    }
}
