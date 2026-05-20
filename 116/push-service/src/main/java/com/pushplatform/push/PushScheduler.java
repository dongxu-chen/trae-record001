package com.pushplatform.push;

import com.pushplatform.common.enums.PushStatusEnum;
import com.pushplatform.entity.PushRecord;
import com.pushplatform.service.PushRecordService;
import com.pushplatform.service.PushTaskService;
import com.pushplatform.service.TokenManageService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;

@Component
public class PushScheduler {

    private static final Logger logger = LoggerFactory.getLogger(PushScheduler.class);

    @Autowired
    private PushRecordService pushRecordService;

    @Autowired
    private PushTaskService pushTaskService;

    @Autowired
    private TokenManageService tokenManageService;

    @Resource(name = "pushBusinessExecutor")
    private Executor pushBusinessExecutor;

    private final Map<String, PushChannel> channelMap = new ConcurrentHashMap<>();

    @Autowired
    public void setChannels(List<PushChannel> channels) {
        for (PushChannel channel : channels) {
            channelMap.put(channel.getChannel(), channel);
        }
    }

    @Scheduled(fixedDelay = 5000)
    public void processPushTasks() {
        try {
            List<PushRecord> records = pushRecordService.listPendingRecords(null, 100);
            if (records.isEmpty()) {
                return;
            }

            logger.info("Processing {} push records", records.size());

            for (PushRecord record : records) {
                pushBusinessExecutor.execute(() -> processSingleRecord(record));
            }
        } catch (Exception e) {
            logger.error("Process push tasks error", e);
        }
    }

    private void processSingleRecord(PushRecord record) {
        PushChannel channel = channelMap.get(record.getChannel());
        if (channel == null) {
            logger.warn("No push channel found for: {}", record.getChannel());
            pushRecordService.updateStatus(record.getId(), PushStatusEnum.FAILED.getCode(), 
                    "Channel not found", null);
            return;
        }

        try {
            PushResult result = channel.send(record);
            if (result.isSuccess()) {
                pushRecordService.updateStatus(record.getId(), PushStatusEnum.SUCCESS.getCode(), 
                        null, result.getMessageId());
                updateTaskCount(record.getTaskId(), true);
            } else {
                pushRecordService.updateStatus(record.getId(), PushStatusEnum.FAILED.getCode(), 
                        result.getErrorMsg(), null);
                updateTaskCount(record.getTaskId(), false);
                
                if (tokenManageService.isTokenInvalid(result.getErrorMsg())) {
                    tokenManageService.asyncCleanInvalidToken(record.getChannel(), record.getTarget());
                }
            }
        } catch (Exception e) {
            logger.error("Push failed for record: {}", record.getId(), e);
            pushRecordService.updateStatus(record.getId(), PushStatusEnum.FAILED.getCode(), 
                    e.getMessage(), null);
            updateTaskCount(record.getTaskId(), false);
            
            if (tokenManageService.isTokenInvalid(e.getMessage())) {
                tokenManageService.asyncCleanInvalidToken(record.getChannel(), record.getTarget());
            }
        }
    }

    private void updateTaskCount(Long taskId, boolean success) {
        if (taskId == null) {
            return;
        }
    }
}
