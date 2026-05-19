package com.logplatform.task;

import com.logplatform.service.AsyncExportService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class ExportCleanupTask {

    private final AsyncExportService asyncExportService;

    @Value("${export.max-age-minutes:360}")
    private long maxAgeMinutes;

    @Scheduled(fixedRateString = "${export.cleanup-interval-minutes:60}000")
    public void cleanupOldExports() {
        log.info("Starting export cleanup task, max age: {} minutes", maxAgeMinutes);
        asyncExportService.cleanupOldTasks(maxAgeMinutes);
        log.info("Export cleanup task completed");
    }
}
