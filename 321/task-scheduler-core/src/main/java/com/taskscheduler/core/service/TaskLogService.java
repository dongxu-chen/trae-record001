package com.taskscheduler.core.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taskscheduler.common.dto.PageResult;
import com.taskscheduler.common.dto.TaskLogQueryDTO;
import com.taskscheduler.common.entity.TaskLog;
import com.taskscheduler.core.mapper.TaskLogMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TaskLogService {

    @Autowired
    private TaskLogMapper taskLogMapper;

    public PageResult<TaskLog> queryTaskLogs(TaskLogQueryDTO queryDTO) {
        Page<TaskLog> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        QueryWrapper<TaskLog> wrapper = new QueryWrapper<>();
        if (queryDTO.getTaskId() != null) {
            wrapper.eq("task_id", queryDTO.getTaskId());
        }
        if (queryDTO.getTaskName() != null && !queryDTO.getTaskName().isEmpty()) {
            wrapper.like("task_name", queryDTO.getTaskName());
        }
        if (queryDTO.getTriggerCode() != null) {
            wrapper.eq("trigger_code", queryDTO.getTriggerCode());
        }
        if (queryDTO.getExecuteCode() != null) {
            wrapper.eq("execute_code", queryDTO.getExecuteCode());
        }
        if (queryDTO.getStartTime() != null) {
            wrapper.ge("trigger_time", queryDTO.getStartTime());
        }
        if (queryDTO.getEndTime() != null) {
            wrapper.le("trigger_time", queryDTO.getEndTime());
        }
        wrapper.orderByDesc("trigger_time");
        Page<TaskLog> result = taskLogMapper.selectPage(page, wrapper);
        return new PageResult<>(result.getTotal(), queryDTO.getPageNum(), queryDTO.getPageSize(), result.getRecords());
    }

    public TaskLog getTaskLogById(Long id) {
        return taskLogMapper.selectById(id);
    }

    public List<TaskLog> getTaskLogsByTaskId(Long taskId, int limit) {
        return taskLogMapper.selectList(
                new QueryWrapper<TaskLog>()
                        .eq("task_id", taskId)
                        .orderByDesc("trigger_time")
                        .last("LIMIT " + limit)
        );
    }

    public void clearLogs(Integer days) {
        QueryWrapper<TaskLog> wrapper = new QueryWrapper<>();
        if (days != null && days > 0) {
            wrapper.apply("create_time < DATE_SUB(NOW(), INTERVAL " + days + " DAY)");
        }
        taskLogMapper.delete(wrapper);
    }
}
