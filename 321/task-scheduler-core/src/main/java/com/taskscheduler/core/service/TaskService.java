package com.taskscheduler.core.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.taskscheduler.common.dto.PageResult;
import com.taskscheduler.common.dto.TaskQueryDTO;
import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.enums.ExecuteTypeEnum;
import com.taskscheduler.common.enums.TaskStatusEnum;
import com.taskscheduler.common.enums.TaskTypeEnum;
import com.taskscheduler.common.util.CronUtils;
import com.taskscheduler.core.mapper.TaskInfoMapper;
import com.taskscheduler.core.scheduler.QuartzSchedulerManager;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;
import java.util.List;

@Slf4j
@Service
public class TaskService {

    @Autowired
    private TaskInfoMapper taskInfoMapper;

    @Autowired
    private QuartzSchedulerManager quartzSchedulerManager;

    @Autowired
    private TaskScheduleService taskScheduleService;

    public PageResult<TaskInfo> queryTasks(TaskQueryDTO queryDTO) {
        Page<TaskInfo> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        QueryWrapper<TaskInfo> wrapper = new QueryWrapper<>();
        if (queryDTO.getTaskName() != null && !queryDTO.getTaskName().isEmpty()) {
            wrapper.like("task_name", queryDTO.getTaskName());
        }
        if (queryDTO.getTaskGroup() != null && !queryDTO.getTaskGroup().isEmpty()) {
            wrapper.eq("task_group", queryDTO.getTaskGroup());
        }
        if (queryDTO.getTaskType() != null) {
            wrapper.eq("task_type", queryDTO.getTaskType());
        }
        if (queryDTO.getStatus() != null) {
            wrapper.eq("status", queryDTO.getStatus());
        }
        wrapper.orderByDesc("create_time");
        Page<TaskInfo> result = taskInfoMapper.selectPage(page, wrapper);
        return new PageResult<>(result.getTotal(), queryDTO.getPageNum(), queryDTO.getPageSize(), result.getRecords());
    }

    public TaskInfo getTaskById(Long id) {
        return taskInfoMapper.selectById(id);
    }

    @Transactional(rollbackFor = Exception.class)
    public void addTask(TaskInfo taskInfo) throws Exception {
        if (taskInfo.getTaskType().equals(TaskTypeEnum.CRON.getCode())) {
            if (!CronUtils.isValid(taskInfo.getCronExpression())) {
                throw new RuntimeException("无效的Cron表达式");
            }
        }

        taskInfo.setStatus(TaskStatusEnum.STOPPED.getCode());
        taskInfo.setCreateTime(LocalDateTime.now());
        taskInfo.setUpdateTime(LocalDateTime.now());
        taskInfoMapper.insert(taskInfo);

        if (taskInfo.getTaskType().equals(TaskTypeEnum.CRON.getCode())) {
            quartzSchedulerManager.addJob(taskInfo);
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public void updateTask(TaskInfo taskInfo) throws Exception {
        TaskInfo exist = taskInfoMapper.selectById(taskInfo.getId());
        if (exist == null) {
            throw new RuntimeException("任务不存在");
        }

        if (taskInfo.getTaskType() != null && taskInfo.getTaskType().equals(TaskTypeEnum.CRON.getCode())) {
            if (taskInfo.getCronExpression() != null && !CronUtils.isValid(taskInfo.getCronExpression())) {
                throw new RuntimeException("无效的Cron表达式");
            }
        }

        taskInfo.setUpdateTime(LocalDateTime.now());
        taskInfoMapper.updateById(taskInfo);

        TaskInfo updated = taskInfoMapper.selectById(taskInfo.getId());
        if (updated.getTaskType().equals(TaskTypeEnum.CRON.getCode())
                && updated.getStatus().equals(TaskStatusEnum.RUNNING.getCode())) {
            quartzSchedulerManager.updateJob(updated);
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public void deleteTask(Long id) throws Exception {
        TaskInfo task = taskInfoMapper.selectById(id);
        if (task == null) {
            throw new RuntimeException("任务不存在");
        }

        if (task.getTaskType().equals(TaskTypeEnum.CRON.getCode())) {
            quartzSchedulerManager.deleteJob(task);
        }

        taskInfoMapper.deleteById(id);
    }

    @Transactional(rollbackFor = Exception.class)
    public void startTask(Long id) throws Exception {
        TaskInfo task = taskInfoMapper.selectById(id);
        if (task == null) {
            throw new RuntimeException("任务不存在");
        }

        task.setStatus(TaskStatusEnum.RUNNING.getCode());
        task.setUpdateTime(LocalDateTime.now());
        taskInfoMapper.updateById(task);

        if (task.getTaskType().equals(TaskTypeEnum.CRON.getCode())) {
            quartzSchedulerManager.addJob(task);
            Date nextFireTime = quartzSchedulerManager.getNextFireTime(task);
            if (nextFireTime != null) {
                task.setNextExecuteTime(nextFireTime.toInstant()
                        .atZone(ZoneId.systemDefault())
                        .toLocalDateTime());
                taskInfoMapper.updateById(task);
            }
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public void stopTask(Long id) throws Exception {
        TaskInfo task = taskInfoMapper.selectById(id);
        if (task == null) {
            throw new RuntimeException("任务不存在");
        }

        task.setStatus(TaskStatusEnum.STOPPED.getCode());
        task.setUpdateTime(LocalDateTime.now());
        taskInfoMapper.updateById(task);

        if (task.getTaskType().equals(TaskTypeEnum.CRON.getCode())) {
            quartzSchedulerManager.pauseJob(task);
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public void triggerTask(Long id) throws Exception {
        TaskInfo task = taskInfoMapper.selectById(id);
        if (task == null) {
            throw new RuntimeException("任务不存在");
        }

        taskScheduleService.triggerTask(task, ExecuteTypeEnum.MANUAL, null);
    }

    public List<TaskInfo> getAllRunningCronTasks() {
        return taskInfoMapper.selectList(
                new QueryWrapper<TaskInfo>()
                        .eq("task_type", TaskTypeEnum.CRON.getCode())
                        .eq("status", TaskStatusEnum.RUNNING.getCode())
        );
    }

    @Transactional(rollbackFor = Exception.class)
    public void initAllCronTasks() throws Exception {
        List<TaskInfo> runningTasks = getAllRunningCronTasks();
        for (TaskInfo task : runningTasks) {
            quartzSchedulerManager.addJob(task);
            Date nextFireTime = quartzSchedulerManager.getNextFireTime(task);
            if (nextFireTime != null) {
                task.setNextExecuteTime(nextFireTime.toInstant()
                        .atZone(ZoneId.systemDefault())
                        .toLocalDateTime());
                taskInfoMapper.updateById(task);
            }
        }
        log.info("Initialized {} cron tasks", runningTasks.size());
    }
}
