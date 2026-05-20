package com.filestorage.task;

import com.filestorage.service.FileShareService;
import com.filestorage.service.FileUploadService;
import com.filestorage.service.RecycleBinService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import jakarta.annotation.Resource;

@Slf4j
@Component
public class ScheduledTasks {

    @Resource
    private FileUploadService fileUploadService;

    @Resource
    private FileShareService fileShareService;

    @Resource
    private RecycleBinService recycleBinService;

    @Scheduled(cron = "0 0 2 * * ?")
    public void cleanupExpiredChunks() {
        try {
            fileUploadService.cleanupExpiredChunks();
        } catch (Exception e) {
            log.error("清理过期分片失败", e);
        }
    }

    @Scheduled(cron = "0 0 3 * * ?")
    public void cleanupExpiredShares() {
        try {
            fileShareService.expireShares();
        } catch (Exception e) {
            log.error("清理过期分享失败", e);
        }
    }

    @Scheduled(cron = "0 0 * * * ?")
    public void cleanupExpiredRecycleBinByTTL() {
        try {
            recycleBinService.cleanupExpiredByTTL();
        } catch (Exception e) {
            log.error("TTL清理回收站过期文件失败", e);
        }
    }

    @Scheduled(cron = "0 0 4 * * ?")
    public void cleanupExpiredRecycleBin() {
        try {
            recycleBinService.cleanupExpiredFilesWithPhysicalDelete();
        } catch (Exception e) {
            log.error("清理回收站过期文件失败", e);
        }
    }
}
