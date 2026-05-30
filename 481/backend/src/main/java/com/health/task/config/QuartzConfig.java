package com.health.task.config;

import com.health.task.job.HealthScoreCalculationJob;
import com.health.task.job.SimulatedTaskJob;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.quartz.*;
import org.springframework.context.annotation.Configuration;

import jakarta.annotation.PostConstruct;
import java.util.List;

@Configuration
@RequiredArgsConstructor
@Slf4j
public class QuartzConfig {

    private final Scheduler scheduler;

    private static final List<TaskDefinition> TASK_DEFINITIONS = List.of(
            new TaskDefinition("DataSyncJob", "DEFAULT", "0 */2 * * * ?"),
            new TaskDefinition("ReportGenerateJob", "DEFAULT", "0 */5 * * * ?"),
            new TaskDefinition("CacheCleanJob", "DEFAULT", "0 */3 * * * ?"),
            new TaskDefinition("EmailNotifyJob", "DEFAULT", "0 */4 * * * ?"),
            new TaskDefinition("LogArchiveJob", "DEFAULT", "0 */6 * * * ?"),
            new TaskDefinition("BackupJob", "DEFAULT", "0 */8 * * * ?"),
            new TaskDefinition("IndexRebuildJob", "DEFAULT", "0 */10 * * * ?")
    );

    @PostConstruct
    public void scheduleJobs() throws SchedulerException {
        for (TaskDefinition def : TASK_DEFINITIONS) {
            scheduleSimulatedTask(def);
        }
        scheduleHealthScoreCalculation();
        log.info("All Quartz jobs scheduled successfully");
    }

    private void scheduleSimulatedTask(TaskDefinition def) throws SchedulerException {
        JobDataMap dataMap = new JobDataMap();
        dataMap.put("taskName", def.name);
        dataMap.put("taskGroup", def.group);
        dataMap.put("cronExpression", def.cron);

        JobDetail jobDetail = JobBuilder.newJob(SimulatedTaskJob.class)
                .withIdentity(def.name, def.group)
                .usingJobData(dataMap)
                .storeDurably()
                .build();

        CronTrigger trigger = TriggerBuilder.newTrigger()
                .withIdentity(def.name + "_trigger", def.group)
                .withSchedule(CronScheduleBuilder.cronSchedule(def.cron)
                        .withMisfireHandlingInstructionFireAndProceed())
                .build();

        scheduler.scheduleJob(jobDetail, trigger);
    }

    private void scheduleHealthScoreCalculation() throws SchedulerException {
        JobDetail jobDetail = JobBuilder.newJob(HealthScoreCalculationJob.class)
                .withIdentity("HealthScoreCalcJob", "SYSTEM")
                .storeDurably()
                .build();

        CronTrigger trigger = TriggerBuilder.newTrigger()
                .withIdentity("HealthScoreCalcJob_trigger", "SYSTEM")
                .withSchedule(CronScheduleBuilder.cronSchedule("0 */1 * * * ?")
                        .withMisfireHandlingInstructionFireAndProceed())
                .build();

        scheduler.scheduleJob(jobDetail, trigger);
    }

    private record TaskDefinition(String name, String group, String cron) {}
}
