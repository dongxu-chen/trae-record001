package com.taskscheduler.core.scheduler;

import com.taskscheduler.common.entity.TaskInfo;
import com.taskscheduler.common.enums.TaskTypeEnum;
import com.taskscheduler.common.util.CronUtils;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.quartz.*;
import org.quartz.impl.StdSchedulerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.Date;

@Component
public class QuartzSchedulerManager {

    private Scheduler scheduler;

    @Autowired
    private SpringJobFactory springJobFactory;

    @PostConstruct
    public void init() throws SchedulerException {
        StdSchedulerFactory factory = new StdSchedulerFactory();
        scheduler = factory.getScheduler();
        scheduler.setJobFactory(springJobFactory);
        scheduler.start();
    }

    @PreDestroy
    public void destroy() throws SchedulerException {
        if (scheduler != null && !scheduler.isShutdown()) {
            scheduler.shutdown();
        }
    }

    public void addJob(TaskInfo taskInfo) throws SchedulerException {
        if (taskInfo.getTaskType() == null || !taskInfo.getTaskType().equals(TaskTypeEnum.CRON.getCode())) {
            return;
        }

        String cron = taskInfo.getCronExpression();
        if (!CronUtils.isValid(cron)) {
            throw new RuntimeException("Invalid cron expression: " + cron);
        }

        JobKey jobKey = getJobKey(taskInfo);
        TriggerKey triggerKey = getTriggerKey(taskInfo);

        if (scheduler.checkExists(jobKey)) {
            scheduler.deleteJob(jobKey);
        }

        JobDetail jobDetail = JobBuilder.newJob(QuartzJob.class)
                .withIdentity(jobKey)
                .usingJobData(QuartzJob.TASK_ID_KEY, taskInfo.getId())
                .storeDurably()
                .build();

        CronTrigger trigger = TriggerBuilder.newTrigger()
                .withIdentity(triggerKey)
                .withSchedule(CronScheduleBuilder.cronSchedule(cron))
                .build();

        scheduler.scheduleJob(jobDetail, trigger);

        if (taskInfo.getStatus() == 0) {
            pauseJob(taskInfo);
        }
    }

    public void updateJob(TaskInfo taskInfo) throws SchedulerException {
        deleteJob(taskInfo);
        addJob(taskInfo);
    }

    public void deleteJob(TaskInfo taskInfo) throws SchedulerException {
        JobKey jobKey = getJobKey(taskInfo);
        if (scheduler.checkExists(jobKey)) {
            scheduler.deleteJob(jobKey);
        }
    }

    public void pauseJob(TaskInfo taskInfo) throws SchedulerException {
        JobKey jobKey = getJobKey(taskInfo);
        if (scheduler.checkExists(jobKey)) {
            scheduler.pauseJob(jobKey);
        }
    }

    public void resumeJob(TaskInfo taskInfo) throws SchedulerException {
        JobKey jobKey = getJobKey(taskInfo);
        if (scheduler.checkExists(jobKey)) {
            scheduler.resumeJob(jobKey);
        }
    }

    public void triggerJob(TaskInfo taskInfo) throws SchedulerException {
        JobKey jobKey = getJobKey(taskInfo);
        if (scheduler.checkExists(jobKey)) {
            scheduler.triggerJob(jobKey);
        }
    }

    public Date getNextFireTime(TaskInfo taskInfo) throws SchedulerException {
        TriggerKey triggerKey = getTriggerKey(taskInfo);
        Trigger trigger = scheduler.getTrigger(triggerKey);
        if (trigger != null) {
            return trigger.getNextFireTime();
        }
        return CronUtils.getNextValidTimeAfter(taskInfo.getCronExpression(), new Date());
    }

    private JobKey getJobKey(TaskInfo taskInfo) {
        return JobKey.jobKey(taskInfo.getTaskGroup() + "_" + taskInfo.getId(), taskInfo.getTaskGroup());
    }

    private TriggerKey getTriggerKey(TaskInfo taskInfo) {
        return TriggerKey.triggerKey(taskInfo.getTaskGroup() + "_" + taskInfo.getId(), taskInfo.getTaskGroup());
    }

    public Scheduler getScheduler() {
        return scheduler;
    }
}
