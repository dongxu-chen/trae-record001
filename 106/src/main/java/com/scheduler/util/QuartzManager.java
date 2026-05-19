package com.scheduler.util;

import com.scheduler.dto.JobDTO;
import com.scheduler.entity.JobConfig;
import com.scheduler.repository.JobConfigRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.quartz.*;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;

@Component
public class QuartzManager {

    @Resource
    private Scheduler scheduler;

    @Resource
    private JobConfigRepository jobConfigRepository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Transactional
    @SuppressWarnings("unchecked")
    public void addJob(JobDTO jobDTO) throws Exception {
        String cronError = CronUtils.validate(jobDTO.getCronExpression());
        if (cronError != null) {
            throw new IllegalArgumentException(cronError);
        }

        Class<? extends Job> jobClass;
        try {
            jobClass = (Class<? extends Job>) Class.forName(jobDTO.getJobClassName());
        } catch (ClassNotFoundException e) {
            throw new IllegalArgumentException("执行类不存在: " + jobDTO.getJobClassName());
        }

        if (!Job.class.isAssignableFrom(jobClass)) {
            throw new IllegalArgumentException("执行类必须实现Job接口: " + jobDTO.getJobClassName());
        }
        
        JobDetail jobDetail = JobBuilder.newJob(jobClass)
                .withIdentity(jobDTO.getJobName(), jobDTO.getJobGroup())
                .withDescription(jobDTO.getDescription())
                .storeDurably()
                .requestRecovery()
                .build();

        CronTrigger trigger = TriggerBuilder.newTrigger()
                .withIdentity(jobDTO.getJobName(), jobDTO.getJobGroup())
                .withSchedule(CronScheduleBuilder.cronSchedule(jobDTO.getCronExpression())
                        .withMisfireHandlingInstructionDoNothing())
                .build();

        scheduler.scheduleJob(jobDetail, trigger);

        saveJobConfig(jobDTO);
    }

    private void saveJobConfig(JobDTO jobDTO) throws Exception {
        JobConfig config = new JobConfig();
        config.setJobName(jobDTO.getJobName());
        config.setJobGroup(jobDTO.getJobGroup());
        config.setDescription(jobDTO.getDescription());
        config.setRetryCount(jobDTO.getRetryCount() != null ? jobDTO.getRetryCount() : 0);
        config.setRetryInterval(jobDTO.getRetryInterval() != null ? jobDTO.getRetryInterval() : 30000);
        config.setTimeoutSeconds(jobDTO.getTimeoutSeconds() != null ? jobDTO.getTimeoutSeconds() : 300);

        if (jobDTO.getDependsOn() != null && !jobDTO.getDependsOn().isEmpty()) {
            config.setDependsOn(objectMapper.writeValueAsString(jobDTO.getDependsOn()));
        }

        jobConfigRepository.save(config);
    }

    @Transactional
    public void updateJob(JobDTO jobDTO) throws Exception {
        String cronError = CronUtils.validate(jobDTO.getCronExpression());
        if (cronError != null) {
            throw new IllegalArgumentException(cronError);
        }

        TriggerKey triggerKey = TriggerKey.triggerKey(jobDTO.getJobName(), jobDTO.getJobGroup());
        CronTrigger trigger = (CronTrigger) scheduler.getTrigger(triggerKey);

        if (trigger == null) {
            throw new Exception("任务不存在");
        }

        CronTrigger newTrigger = TriggerBuilder.newTrigger()
                .withIdentity(triggerKey)
                .withSchedule(CronScheduleBuilder.cronSchedule(jobDTO.getCronExpression())
                        .withMisfireHandlingInstructionDoNothing())
                .build();

        scheduler.rescheduleJob(triggerKey, newTrigger);
        updateJobConfig(jobDTO);
    }

    @Transactional
    public void deleteJob(String jobName, String jobGroup) throws Exception {
        JobKey jobKey = JobKey.jobKey(jobName, jobGroup);
        scheduler.deleteJob(jobKey);
        jobConfigRepository.deleteByJobNameAndJobGroup(jobName, jobGroup);
    }

    private void updateJobConfig(JobDTO jobDTO) throws Exception {
        JobConfig config = jobConfigRepository.findByJobNameAndJobGroup(jobDTO.getJobName(), jobDTO.getJobGroup())
                .orElse(new JobConfig());
        config.setJobName(jobDTO.getJobName());
        config.setJobGroup(jobDTO.getJobGroup());
        config.setDescription(jobDTO.getDescription());
        config.setRetryCount(jobDTO.getRetryCount() != null ? jobDTO.getRetryCount() : 0);
        config.setRetryInterval(jobDTO.getRetryInterval() != null ? jobDTO.getRetryInterval() : 30000);
        config.setTimeoutSeconds(jobDTO.getTimeoutSeconds() != null ? jobDTO.getTimeoutSeconds() : 300);

        if (jobDTO.getDependsOn() != null && !jobDTO.getDependsOn().isEmpty()) {
            config.setDependsOn(objectMapper.writeValueAsString(jobDTO.getDependsOn()));
        } else {
            config.setDependsOn(null);
        }

        jobConfigRepository.save(config);
    }

    public void pauseJob(String jobName, String jobGroup) throws Exception {
        JobKey jobKey = JobKey.jobKey(jobName, jobGroup);
        scheduler.pauseJob(jobKey);
    }

    public void resumeJob(String jobName, String jobGroup) throws Exception {
        JobKey jobKey = JobKey.jobKey(jobName, jobGroup);
        scheduler.resumeJob(jobKey);
    }

    public void triggerJob(String jobName, String jobGroup) throws Exception {
        JobKey jobKey = JobKey.jobKey(jobName, jobGroup);
        scheduler.triggerJob(jobKey);
    }

    public boolean checkJobExists(String jobName, String jobGroup) throws Exception {
        JobKey jobKey = JobKey.jobKey(jobName, jobGroup);
        return scheduler.checkExists(jobKey);
    }

    public Trigger.TriggerState getJobState(String jobName, String jobGroup) throws Exception {
        TriggerKey triggerKey = TriggerKey.triggerKey(jobName, jobGroup);
        return scheduler.getTriggerState(triggerKey);
    }

}
