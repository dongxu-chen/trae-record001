package com.scheduler.listener;

import com.scheduler.entity.JobConfig;
import com.scheduler.entity.JobExecuteRecord;
import com.scheduler.entity.JobRetryRecord;
import com.scheduler.repository.JobConfigRepository;
import com.scheduler.repository.JobExecuteRecordRepository;
import com.scheduler.repository.JobRetryRecordRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.quartz.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;

@Component
public class JobExecutionListener implements JobListener {

    private static final Logger logger = LoggerFactory.getLogger(JobExecutionListener.class);
    private static final String NAME = "JobExecutionListener";

    private final Map<String, Future<?>> runningJobs = new ConcurrentHashMap<>();
    private final ExecutorService timeoutExecutor = Executors.newCachedThreadPool();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Resource
    private JobConfigRepository jobConfigRepository;

    @Resource
    private JobExecuteRecordRepository jobExecuteRecordRepository;

    @Resource
    private JobRetryRecordRepository jobRetryRecordRepository;

    @Resource
    private Scheduler scheduler;

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public void jobToBeExecuted(JobExecutionContext context) {
        JobKey jobKey = context.getJobDetail().getKey();
        String jobName = jobKey.getName();
        String jobGroup = jobKey.getGroup();

        logger.info("任务即将执行: {}.{}", jobGroup, jobName);

        try {
            JobConfig config = jobConfigRepository.findByJobNameAndJobGroup(jobName, jobGroup).orElse(null);
            if (config == null) {
                return;
            }

            if (!checkDependencies(config)) {
                logger.warn("任务 {}.{} 依赖检查不通过，跳过执行", jobGroup, jobName);
                return;
            }

            setupTimeoutMonitor(context, config);
            context.put("retryCount", 0);

        } catch (Exception e) {
            logger.error("任务执行前处理失败", e);
        }
    }

    private boolean checkDependencies(JobConfig config) {
        if (config.getDependsOn() == null || config.getDependsOn().isEmpty()) {
            return true;
        }

        try {
            List<String> dependencies = objectMapper.readValue(config.getDependsOn(),
                    new TypeReference<List<String>>() {});

            for (String dependency : dependencies) {
                String[] parts = dependency.split(":");
                String depName = parts[0];
                String depGroup = parts.length > 1 ? parts[1] : "DEFAULT";

                JobExecuteRecord lastRecord = jobExecuteRecordRepository
                        .findFirstByJobNameAndJobGroupOrderByExecuteTimeDesc(depName, depGroup)
                        .orElse(null);

                if (lastRecord == null || !"SUCCESS".equals(lastRecord.getExecuteStatus())) {
                    logger.warn("依赖任务 {}.{} 未找到或执行失败", depGroup, depName);
                    return false;
                }
            }
            return true;
        } catch (Exception e) {
            logger.error("检查依赖失败", e);
            return false;
        }
    }

    private void setupTimeoutMonitor(JobExecutionContext context, JobConfig config) {
        if (config.getTimeoutSeconds() == null || config.getTimeoutSeconds() <= 0) {
            return;
        }

        String jobKey = context.getJobDetail().getKey().getName() + ":" + context.getJobDetail().getKey().getGroup();
        long timeoutMs = config.getTimeoutSeconds() * 1000L;

        Future<?> timeoutFuture = timeoutExecutor.submit(() -> {
            try {
                Thread.sleep(timeoutMs);
                if (runningJobs.containsKey(jobKey)) {
                    logger.warn("任务 {} 执行超时，将被中断", jobKey);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });

        runningJobs.put(jobKey, timeoutFuture);
    }

    @Override
    public void jobExecutionVetoed(JobExecutionContext context) {
        logger.info("任务执行被否决: {}.{}",
                context.getJobDetail().getKey().getGroup(),
                context.getJobDetail().getKey().getName());
    }

    @Override
    public void jobWasExecuted(JobExecutionContext context, JobExecutionException jobException) {
        JobKey jobKey = context.getJobDetail().getKey();
        String jobName = jobKey.getName();
        String jobGroup = jobKey.getGroup();
        String jobKeyStr = jobName + ":" + jobGroup;

        try {
            Future<?> timeoutFuture = runningJobs.remove(jobKeyStr);
            if (timeoutFuture != null && !timeoutFuture.isDone()) {
                timeoutFuture.cancel(true);
            }

            JobConfig config = jobConfigRepository.findByJobNameAndJobGroup(jobName, jobGroup).orElse(null);

            if (jobException != null && config != null && config.getRetryCount() > 0) {
                handleJobFailure(context, config, jobException);
            }

        } catch (Exception e) {
            logger.error("任务执行后处理失败", e);
        }
    }

    private void handleJobFailure(JobExecutionContext context, JobConfig config, JobExecutionException exception) {
        JobKey jobKey = context.getJobDetail().getKey();
        String jobName = jobKey.getName();
        String jobGroup = jobKey.getGroup();

        try {
            JobRetryRecord lastRetry = jobRetryRecordRepository
                    .findFirstByJobNameAndJobGroupOrderByFireTimeDesc(jobName, jobGroup)
                    .orElse(null);

            int currentRetry = lastRetry != null ? lastRetry.getRetryNumber() + 1 : 1;

            JobRetryRecord retryRecord = new JobRetryRecord();
            retryRecord.setJobName(jobName);
            retryRecord.setJobGroup(jobGroup);
            retryRecord.setFireTime(LocalDateTime.now());
            retryRecord.setRetryNumber(currentRetry);
            retryRecord.setMaxRetries(config.getRetryCount());

            String errorMsg = exception.getMessage();
            if (errorMsg != null && errorMsg.length() > 5000) {
                errorMsg = errorMsg.substring(0, 5000);
            }
            retryRecord.setErrorMessage(errorMsg);

            if (currentRetry <= config.getRetryCount()) {
                retryRecord.setStatus("PENDING_RETRY");
                LocalDateTime nextRetryTime = LocalDateTime.now().plusSeconds(config.getRetryInterval() / 1000);
                retryRecord.setNextRetryTime(nextRetryTime);

                scheduleRetry(jobKey, config, currentRetry);

                logger.info("任务 {}.{} 失败，安排第 {} 次重试，下一次时间: {}",
                        jobGroup, jobName, currentRetry, nextRetryTime);
            } else {
                retryRecord.setStatus("EXHAUSTED");
                logger.warn("任务 {}.{} 重试次数已用完", jobGroup, jobName);
            }

            jobRetryRecordRepository.save(retryRecord);

        } catch (Exception e) {
            logger.error("处理任务失败重试时出错", e);
        }
    }

    private void scheduleRetry(JobKey jobKey, JobConfig config, int retryNumber) throws SchedulerException {
        TriggerKey triggerKey = TriggerKey.triggerKey(jobKey.getName() + "_retry_" + retryNumber, jobKey.getGroup());

        long nextFireTime = System.currentTimeMillis() + config.getRetryInterval();

        SimpleTrigger trigger = TriggerBuilder.newTrigger()
                .withIdentity(triggerKey)
                .forJob(jobKey)
                .startAt(new Date(nextFireTime))
                .withSchedule(SimpleScheduleBuilder.simpleSchedule()
                        .withMisfireHandlingInstructionFireNow())
                .build();

        scheduler.scheduleJob(trigger);
    }

}
