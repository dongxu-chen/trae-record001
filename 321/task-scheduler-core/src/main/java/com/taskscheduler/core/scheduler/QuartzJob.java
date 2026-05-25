package com.taskscheduler.core.scheduler;

import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.enums.ExecuteTypeEnum;
import com.taskscheduler.core.mapper.TaskInfoMapper;
import com.taskscheduler.core.service.TaskScheduleService;
import org.quartz.DisallowConcurrentExecution;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
@DisallowConcurrentExecution
public class QuartzJob implements Job {

    public static final String TASK_ID_KEY = "TASK_ID";

    @Autowired
    private TaskScheduleService taskScheduleService;

    @Autowired
    private TaskInfoMapper taskInfoMapper;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        Long taskId = (Long) context.getMergedJobDataMap().get(TASK_ID_KEY);
        if (taskId == null) {
            throw new JobExecutionException("TaskId is null");
        }
        TaskInfo taskInfo = taskInfoMapper.selectById(taskId);
        if (taskInfo == null) {
            throw new JobExecutionException("TaskInfo not found for id: " + taskId);
        }
        try {
            taskScheduleService.triggerTask(taskInfo, ExecuteTypeEnum.NORMAL, null);
        } catch (Exception e) {
            throw new JobExecutionException(e);
        }
    }
}
