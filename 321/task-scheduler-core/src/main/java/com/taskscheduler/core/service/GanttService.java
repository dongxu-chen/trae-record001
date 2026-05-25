package com.taskscheduler.core.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.taskscheduler.common.dto.GanttTaskDTO;
import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.entity.TaskLog;
import com.taskscheduler.common.enums.TaskPriorityEnum;
import com.taskscheduler.core.mapper.TaskInfoMapper;
import com.taskscheduler.core.mapper.TaskLogMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class GanttService {

    @Autowired
    private TaskLogMapper taskLogMapper;

    @Autowired
    private TaskInfoMapper taskInfoMapper;

    public List<GanttTaskDTO> getGanttData(LocalDateTime startTime, LocalDateTime endTime,
                                            String taskGroup, Long taskId) {
        QueryWrapper<TaskLog> queryWrapper = new QueryWrapper<>();

        if (startTime != null) {
            queryWrapper.ge("execute_start_time", startTime);
        }
        if (endTime != null) {
            queryWrapper.lt("execute_start_time", endTime);
        }
        if (taskGroup != null && !taskGroup.isEmpty()) {
            queryWrapper.eq("task_group", taskGroup);
        }
        if (taskId != null) {
            queryWrapper.eq("task_id", taskId);
        }

        queryWrapper.isNotNull("execute_start_time");
        queryWrapper.orderByAsc("execute_start_time");
        queryWrapper.last("LIMIT 500");

        List<TaskLog> logs = taskLogMapper.selectList(queryWrapper);

        Set<Long> taskIds = logs.stream()
                .map(TaskLog::getTaskId)
                .collect(Collectors.toSet());

        Map<Long, TaskInfo> taskInfoMap = new HashMap<>();
        if (!taskIds.isEmpty()) {
            List<TaskInfo> taskInfos = taskInfoMapper.selectBatchIds(taskIds);
            taskInfoMap = taskInfos.stream()
                    .collect(Collectors.toMap(TaskInfo::getId, t -> t));
        }

        List<GanttTaskDTO> result = new ArrayList<>();
        for (TaskLog log : logs) {
            GanttTaskDTO dto = convertToGanttDTO(log, taskInfoMap.get(log.getTaskId()));
            if (dto != null) {
                result.add(dto);
            }
        }

        return result;
    }

    public List<GanttTaskDTO> getGanttDataByLogId(Long logId) {
        if (logId == null) {
            return Collections.emptyList();
        }

        QueryWrapper<TaskLog> queryWrapper = new QueryWrapper<>();
        queryWrapper.and(w -> w.eq("id", logId).or().eq("parent_log_id", logId));
        queryWrapper.isNotNull("execute_start_time");
        queryWrapper.orderByAsc("execute_start_time");

        List<TaskLog> logs = taskLogMapper.selectList(queryWrapper);

        Set<Long> taskIds = logs.stream()
                .map(TaskLog::getTaskId)
                .collect(Collectors.toSet());

        Map<Long, TaskInfo> taskInfoMap = new HashMap<>();
        if (!taskIds.isEmpty()) {
            List<TaskInfo> taskInfos = taskInfoMapper.selectBatchIds(taskIds);
            taskInfoMap = taskInfos.stream()
                    .collect(Collectors.toMap(TaskInfo::getId, t -> t));
        }

        List<GanttTaskDTO> result = new ArrayList<>();
        for (TaskLog log : logs) {
            GanttTaskDTO dto = convertToGanttDTO(log, taskInfoMap.get(log.getTaskId()));
            if (dto != null) {
                result.add(dto);
            }
        }

        return result;
    }

    private GanttTaskDTO convertToGanttDTO(TaskLog log, TaskInfo taskInfo) {
        if (log.getExecuteStartTime() == null) {
            return null;
        }

        GanttTaskDTO dto = new GanttTaskDTO();
        dto.setId(log.getId());
        dto.setTaskId(log.getTaskId());
        dto.setTaskName(log.getTaskName());
        dto.setTaskGroup(log.getTaskGroup());
        dto.setShardingIndex(log.getShardingIndex());
        dto.setShardingTotal(log.getShardingTotal());
        dto.setStartTime(log.getExecuteStartTime());
        dto.setEndTime(log.getExecuteEndTime());
        dto.setExecuteCode(log.getExecuteCode());
        dto.setExecuteMsg(log.getExecuteMsg());

        if (log.getExecuteEndTime() != null) {
            long seconds = Duration.between(log.getExecuteStartTime(), log.getExecuteEndTime()).getSeconds();
            dto.setDuration(seconds);
        }

        if (log.getExecuteCode() == null) {
            dto.setStatus("running");
        } else if (log.getExecuteCode() == 0) {
            dto.setStatus("success");
        } else {
            dto.setStatus("failed");
        }

        if (taskInfo != null && taskInfo.getPriority() != null) {
            TaskPriorityEnum priority = TaskPriorityEnum.getByCode(taskInfo.getPriority());
            dto.setPriority(priority.getDesc());
        } else {
            dto.setPriority(TaskPriorityEnum.NORMAL.getDesc());
        }

        return dto;
    }

    public Map<String, Object> getGanttStats(LocalDateTime startTime, LocalDateTime endTime) {
        QueryWrapper<TaskLog> queryWrapper = new QueryWrapper<>();
        if (startTime != null) {
            queryWrapper.ge("execute_start_time", startTime);
        }
        if (endTime != null) {
            queryWrapper.lt("execute_start_time", endTime);
        }
        queryWrapper.isNotNull("execute_start_time");

        List<TaskLog> logs = taskLogMapper.selectList(queryWrapper);

        Map<String, Object> stats = new HashMap<>();
        int totalTasks = logs.size();
        int successCount = 0;
        int failedCount = 0;
        int runningCount = 0;
        long totalDuration = 0;
        long maxDuration = 0;
        long minDuration = Long.MAX_VALUE;
        int countWithDuration = 0;

        for (TaskLog log : logs) {
            if (log.getExecuteCode() == null) {
                runningCount++;
            } else if (log.getExecuteCode() == 0) {
                successCount++;
            } else {
                failedCount++;
            }

            if (log.getExecuteStartTime() != null && log.getExecuteEndTime() != null) {
                long seconds = Duration.between(log.getExecuteStartTime(), log.getExecuteEndTime()).getSeconds();
                totalDuration += seconds;
                maxDuration = Math.max(maxDuration, seconds);
                minDuration = Math.min(minDuration, seconds);
                countWithDuration++;
            }
        }

        stats.put("totalTasks", totalTasks);
        stats.put("successCount", successCount);
        stats.put("failedCount", failedCount);
        stats.put("runningCount", runningCount);
        stats.put("successRate", totalTasks > 0 ? (double) successCount / totalTasks * 100 : 0);
        stats.put("avgDuration", countWithDuration > 0 ? (double) totalDuration / countWithDuration : 0);
        stats.put("maxDuration", maxDuration);
        stats.put("minDuration", minDuration == Long.MAX_VALUE ? 0 : minDuration);

        return stats;
    }

    public List<String> getTaskGroups() {
        List<TaskInfo> tasks = taskInfoMapper.selectList(
                new QueryWrapper<TaskInfo>().select("distinct task_group")
        );
        return tasks.stream()
                .map(TaskInfo::getTaskGroup)
                .filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.toList());
    }
}
