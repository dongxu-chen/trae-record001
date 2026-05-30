package com.taskflow.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class SchedulerService {

    private final TriggerService triggerService;

    @Scheduled(cron = "0 * * * * ?")
    public void checkCronTriggers() {
        log.debug("Checking cron triggers...");
        triggerService.fireCronTriggers();
    }
}
