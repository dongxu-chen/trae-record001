package com.taskscheduler.core.dag;

import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.entity.TaskLog;
import com.taskscheduler.common.enums.TaskTypeEnum;
import com.taskscheduler.core.mapper.TaskInfoMapper;
import com.taskscheduler.core.mapper.TaskLogMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Component
public class DagTaskScheduler {

    @Autowired
    private TaskInfoMapper taskInfoMapper;

    @Autowired
    private TaskLogMapper taskLogMapper;

    private volatile long lastCacheUpdateTime = 0;
    private static final long CACHE_EXPIRE_TIME = 60_000L;

    private final Map<Long, List<Long>> dagDependenciesCache = new ConcurrentHashMap<>();
    private final Map<Long, TaskInfo> taskInfoCache = new ConcurrentHashMap<>();
    private volatile List<TaskInfo> topologicalOrderCache = new ArrayList<>();
    private volatile Boolean hasCycleCache = null;
    private volatile Set<Long> cycleFreeTasksCache = ConcurrentHashMap.newKeySet();

    public List<Long> parseDependencies(String dagDependencies) {
        if (dagDependencies == null || dagDependencies.trim().isEmpty()) {
            return Collections.emptyList();
        }
        return Arrays.stream(dagDependencies.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .map(Long::parseLong)
                .collect(Collectors.toList());
    }

    private synchronized void refreshCacheIfNeeded() {
        long now = System.currentTimeMillis();
        if (now - lastCacheUpdateTime < CACHE_EXPIRE_TIME && hasCycleCache != null) {
            return;
        }

        log.debug("Refreshing DAG cache");

        List<TaskInfo> dagTasks = taskInfoMapper.selectList(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TaskInfo>()
                        .eq("task_type", TaskTypeEnum.DAG.getCode())
        );

        taskInfoCache.clear();
        dagDependenciesCache.clear();
        for (TaskInfo task : dagTasks) {
            taskInfoCache.put(task.getId(), task);
            dagDependenciesCache.put(task.getId(), parseDependencies(task.getDagDependencies()));
        }

        try {
            topologicalOrderCache = doTopologicalSort(dagTasks);
            hasCycleCache = false;
            cycleFreeTasksCache = taskInfoCache.keySet();
            log.info("DAG topology updated, no cycle detected, total tasks: {}", dagTasks.size());
        } catch (RuntimeException e) {
            topologicalOrderCache = Collections.emptyList();
            hasCycleCache = true;
            cycleFreeTasksCache = findCycleFreeTasks(dagTasks);
            log.warn("DAG has cycle, cycle-free tasks: {}", cycleFreeTasksCache.size());
        }

        lastCacheUpdateTime = now;
    }

    public void invalidateCache() {
        lastCacheUpdateTime = 0;
        hasCycleCache = null;
        log.info("DAG cache invalidated");
    }

    private List<TaskInfo> doTopologicalSort(List<TaskInfo> dagTasks) {
        Map<Long, TaskInfo> taskMap = dagTasks.stream()
                .collect(Collectors.toMap(TaskInfo::getId, t -> t));

        Map<Long, Integer> inDegree = new HashMap<>();
        Map<Long, List<Long>> adjList = new HashMap<>();

        for (TaskInfo task : dagTasks) {
            inDegree.put(task.getId(), 0);
            adjList.put(task.getId(), new ArrayList<>());
        }

        for (TaskInfo task : dagTasks) {
            List<Long> deps = parseDependencies(task.getDagDependencies());
            inDegree.put(task.getId(), deps.size());
            for (Long depId : deps) {
                if (adjList.containsKey(depId)) {
                    adjList.get(depId).add(task.getId());
                }
            }
        }

        Queue<Long> queue = new LinkedList<>();
        for (Map.Entry<Long, Integer> entry : inDegree.entrySet()) {
            if (entry.getValue() == 0) {
                queue.offer(entry.getKey());
            }
        }

        List<TaskInfo> result = new ArrayList<>();
        while (!queue.isEmpty()) {
            Long taskId = queue.poll();
            TaskInfo task = taskMap.get(taskId);
            if (task != null) {
                result.add(task);
            }
            for (Long nextId : adjList.getOrDefault(taskId, Collections.emptyList())) {
                int degree = inDegree.get(nextId) - 1;
                inDegree.put(nextId, degree);
                if (degree == 0) {
                    queue.offer(nextId);
                }
            }
        }

        if (result.size() != dagTasks.size()) {
            throw new RuntimeException("DAG存在循环依赖");
        }

        return result;
    }

    private Set<Long> findCycleFreeTasks(List<TaskInfo> dagTasks) {
        Set<Long> cycleFree = ConcurrentHashMap.newKeySet();
        Map<Long, List<Long>> adjList = new HashMap<>();
        Map<Long, List<Long>> reverseAdjList = new HashMap<>();

        for (TaskInfo task : dagTasks) {
            adjList.put(task.getId(), new ArrayList<>());
            reverseAdjList.put(task.getId(), new ArrayList<>());
        }

        for (TaskInfo task : dagTasks) {
            List<Long> deps = parseDependencies(task.getDagDependencies());
            for (Long depId : deps) {
                if (adjList.containsKey(depId)) {
                    adjList.get(depId).add(task.getId());
                    reverseAdjList.get(task.getId()).add(depId);
                }
            }
        }

        for (TaskInfo task : dagTasks) {
            if (!hasCycle(task.getId(), adjList, reverseAdjList)) {
                cycleFree.add(task.getId());
            }
        }

        return cycleFree;
    }

    private boolean hasCycle(Long startId, Map<Long, List<Long>> adjList, Map<Long, List<Long>> reverseAdjList) {
        Set<Long> visited = new HashSet<>();
        Set<Long> recStack = new HashSet<>();
        return dfsCheckCycle(startId, adjList, visited, recStack)
                || dfsCheckCycle(startId, reverseAdjList, visited, recStack);
    }

    private boolean dfsCheckCycle(Long current, Map<Long, List<Long>> adjList,
                                   Set<Long> visited, Set<Long> recStack) {
        if (recStack.contains(current)) {
            return true;
        }
        if (visited.contains(current)) {
            return false;
        }

        visited.add(current);
        recStack.add(current);

        for (Long next : adjList.getOrDefault(current, Collections.emptyList())) {
            if (dfsCheckCycle(next, adjList, visited, recStack)) {
                return true;
            }
        }

        recStack.remove(current);
        return false;
    }

    public boolean checkDependenciesReady(Long taskId, String dagDependencies) {
        refreshCacheIfNeeded();

        if (Boolean.TRUE.equals(hasCycleCache) && !cycleFreeTasksCache.contains(taskId)) {
            log.debug("Task {} is in cycle, skip", taskId);
            return false;
        }

        if (Boolean.FALSE.equals(hasCycleCache)) {
            return checkDependenciesReadyFast(taskId);
        }

        List<Long> dependencyIds = parseDependencies(dagDependencies);
        if (dependencyIds.isEmpty()) {
            return true;
        }

        return checkDependenciesReadySlow(taskId, dependencyIds);
    }

    private boolean checkDependenciesReadyFast(Long taskId) {
        List<Long> dependencyIds = dagDependenciesCache.get(taskId);
        if (dependencyIds == null || dependencyIds.isEmpty()) {
            return true;
        }

        TaskInfo currentTask = taskInfoCache.get(taskId);
        if (currentTask == null) {
            return false;
        }

        for (Long depId : dependencyIds) {
            TaskInfo depTask = taskInfoCache.get(depId);
            if (depTask == null) {
                return false;
            }

            if (depTask.getLastExecuteTime() == null) {
                return false;
            }

            if (currentTask.getLastExecuteTime() != null
                    && currentTask.getLastExecuteTime().isAfter(depTask.getLastExecuteTime())) {
                continue;
            }

            List<TaskLog> recentLogs = taskLogMapper.selectList(
                    new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TaskLog>()
                            .eq("task_id", depId)
                            .orderByDesc("trigger_time")
                            .last("LIMIT 1")
            );

            if (recentLogs.isEmpty()) {
                return false;
            }

            TaskLog lastLog = recentLogs.get(0);
            if (lastLog.getExecuteCode() == null || lastLog.getExecuteCode() != 0) {
                return false;
            }
        }
        return true;
    }

    private boolean checkDependenciesReadySlow(Long taskId, List<Long> dependencyIds) {
        if (dependencyIds.isEmpty()) {
            return true;
        }

        for (Long depId : dependencyIds) {
            List<TaskLog> recentLogs = taskLogMapper.selectList(
                    new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TaskLog>()
                            .eq("task_id", depId)
                            .orderByDesc("trigger_time")
                            .last("LIMIT 1")
            );

            if (recentLogs.isEmpty()) {
                return false;
            }

            TaskLog lastLog = recentLogs.get(0);
            if (lastLog.getExecuteCode() == null || lastLog.getExecuteCode() != 0) {
                return false;
            }

            TaskInfo depTask = taskInfoMapper.selectById(depId);
            if (depTask != null && depTask.getLastExecuteTime() != null) {
                TaskInfo currentTask = taskInfoMapper.selectById(taskId);
                if (currentTask != null && currentTask.getLastExecuteTime() != null
                        && currentTask.getLastExecuteTime().isAfter(depTask.getLastExecuteTime())) {
                    continue;
                }
            }
        }
        return true;
    }

    public List<TaskInfo> getDagReadyTasks() {
        refreshCacheIfNeeded();

        List<TaskInfo> dagTasks = taskInfoMapper.selectList(
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<TaskInfo>()
                        .eq("task_type", TaskTypeEnum.DAG.getCode())
                        .eq("status", 1)
        );

        List<TaskInfo> readyTasks = new ArrayList<>();
        for (TaskInfo task : topologicalOrderCache) {
            if (task.getStatus() == null || task.getStatus() != 1) {
                continue;
            }
            if (checkDependenciesReady(task.getId(), task.getDagDependencies())) {
                readyTasks.add(task);
            }
        }

        for (TaskInfo task : dagTasks) {
            if (!topologicalOrderCache.contains(task)
                    && task.getStatus() == 1
                    && checkDependenciesReady(task.getId(), task.getDagDependencies())) {
                readyTasks.add(task);
            }
        }

        return readyTasks;
    }

    public List<TaskInfo> topologicalSort() {
        refreshCacheIfNeeded();
        if (Boolean.TRUE.equals(hasCycleCache)) {
            throw new RuntimeException("DAG存在循环依赖");
        }
        return new ArrayList<>(topologicalOrderCache);
    }

    public boolean hasCycle() {
        refreshCacheIfNeeded();
        return Boolean.TRUE.equals(hasCycleCache);
    }

    public List<Long> getTaskDependencies(Long taskId) {
        refreshCacheIfNeeded();
        return dagDependenciesCache.getOrDefault(taskId, Collections.emptyList());
    }
}
