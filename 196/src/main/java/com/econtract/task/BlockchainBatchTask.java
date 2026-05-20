package com.econtract.task;

import com.econtract.service.BlockchainBatchService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;

@Slf4j
@Component
public class BlockchainBatchTask {

    @Resource
    private BlockchainBatchService batchService;

    @Scheduled(fixedRate = 30000)
    public void checkBatch() {
        try {
            int queueSize = batchService.getPendingQueueSize();
            if (queueSize > 0) {
                log.debug("检查存证批量队列, 当前大小: {}", queueSize);
            }
            batchService.checkAndTriggerBatch();
        } catch (Exception e) {
            log.error("批量存证检查失败", e);
        }
    }

    @Scheduled(cron = "0 0 * * * ?")
    public void forceFlushBatch() {
        try {
            int queueSize = batchService.getPendingQueueSize();
            if (queueSize > 0) {
                log.info("整点强制刷新存证批量队列, 数量: {}", queueSize);
                batchService.triggerBatch();
            }
        } catch (Exception e) {
            log.error("强制刷新批量存证失败", e);
        }
    }
}
