package com.datacheck.scheduler;

import com.datacheck.check.CheckEngine;
import com.datacheck.model.CheckTask;
import com.datacheck.model.enums.DataSourceType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.UUID;

@Slf4j
@Component
public class CheckScheduler {

    private final CheckEngine checkEngine;

    @Value("${check.scheduler.enabled:true}")
    private boolean schedulerEnabled;

    @Autowired
    public CheckScheduler(CheckEngine checkEngine) {
        this.checkEngine = checkEngine;
    }

    @Scheduled(cron = "${check.scheduler.cron:0 */1 * * * ?}")
    public void scheduledCheck() {
        if (!schedulerEnabled) {
            return;
        }

        log.debug("Scheduled check triggered");

        if (checkEngine.getRunningTasks().isEmpty()) {
            log.debug("No running tasks, scheduler is idle");
        }
    }

    public void triggerScheduledTask(DataSourceType type, String tableName) {
        if (!schedulerEnabled) {
            log.warn("Scheduler is disabled, cannot trigger scheduled task");
            return;
        }

        CheckTask task = CheckTask.builder()
                .id(UUID.randomUUID().toString())
                .sourceType(type)
                .tableName(tableName)
                .autoRepair(true)
                .build();
        task.setCreatedAt(LocalDateTime.now());
        task.setStatus("PENDING");

        log.info("Triggering scheduled check task for type: {}, table: {}", type, tableName);
        checkEngine.executeCheck(task);
    }
}
