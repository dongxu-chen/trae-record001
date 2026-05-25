package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.sms.platform.common.enums.ReceiptStatusEnum;
import com.sms.platform.common.enums.SendStatusEnum;
import com.sms.platform.entity.SmsChannelConfig;
import com.sms.platform.entity.SmsSendRecord;
import com.sms.platform.mapper.SmsSendRecordMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Service
public class ReceiptService {

    @Resource
    private SmsSendRecordMapper sendRecordMapper;

    @Resource
    private ChannelManagerService channelManagerService;

    private static final int BATCH_SIZE = 100;
    private final Map<Integer, AtomicInteger> channelReceiptTimeoutCount = new ConcurrentHashMap<>();

    @Scheduled(fixedDelay = 5000)
    public void checkReceiptTimeout() {
        LocalDateTime now = LocalDateTime.now();
        int offset = 0;

        while (true) {
            List<SmsSendRecord> timeoutRecords = sendRecordMapper.selectList(
                    new LambdaQueryWrapper<SmsSendRecord>()
                            .eq(SmsSendRecord::getReceiptStatus, ReceiptStatusEnum.PENDING.getCode())
                            .le(SmsSendRecord::getReceiptExpireTime, now)
                            .eq(SmsSendRecord::getDeleted, 0)
                            .last("LIMIT " + BATCH_SIZE + " OFFSET " + offset)
            );

            if (timeoutRecords == null || timeoutRecords.isEmpty()) {
                break;
            }

            for (SmsSendRecord record : timeoutRecords) {
                processReceiptTimeout(record);
            }

            if (timeoutRecords.size() < BATCH_SIZE) {
                break;
            }
            offset += BATCH_SIZE;
        }
    }

    private void processReceiptTimeout(SmsSendRecord record) {
        log.warn("短信回执超时, serialNo={}, mobile={}, channelCode={}, sendTime={}",
                record.getSerialNo(), record.getMobile(), record.getChannelCode(), record.getSendTime());

        LambdaUpdateWrapper<SmsSendRecord> updateWrapper = new LambdaUpdateWrapper<SmsSendRecord>()
                .eq(SmsSendRecord::getId, record.getId())
                .set(SmsSendRecord::getStatus, SendStatusEnum.RECEIPT_TIMEOUT.getCode())
                .set(SmsSendRecord::getReceiptStatus, ReceiptStatusEnum.TIMEOUT.getCode())
                .set(SmsSendRecord::getReceiptTime, LocalDateTime.now())
                .set(SmsSendRecord::getErrorMsg, "回执超时");

        sendRecordMapper.update(null, updateWrapper);

        recordReceiptTimeout(record.getChannelCode());
    }

    public void recordReceiptTimeout(Integer channelCode) {
        AtomicInteger counter = channelReceiptTimeoutCount.computeIfAbsent(channelCode, k -> new AtomicInteger(0));
        int currentTimeoutCount = counter.incrementAndGet();

        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);
        if (config != null) {
            int maxCount = config.getMaxReceiptTimeoutCount() != null ? config.getMaxReceiptTimeoutCount() : 5;
            log.warn("通道 {} 连续回执超时次数: {}/{}", channelCode, currentTimeoutCount, maxCount);

            if (currentTimeoutCount >= maxCount) {
                markChannelUnhealthyByReceiptTimeout(channelCode);
                counter.set(0);
            }

            config.setReceiptTimeoutCount(currentTimeoutCount);
        }
    }

    private void markChannelUnhealthyByReceiptTimeout(Integer channelCode) {
        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);
        if (config != null && config.getIsHealthy() == 1) {
            config.setIsHealthy(0);
            config.setReceiptTimeoutCount(0);
            channelManagerService.updateChannelConfig(config);
            log.error("通道 {} 连续回执超时超过阈值，标记为不健康，触发主动切换", channelCode);
        }
    }

    public void recordReceiptSuccess(Integer channelCode) {
        AtomicInteger counter = channelReceiptTimeoutCount.get(channelCode);
        if (counter != null) {
            counter.set(0);
        }

        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);
        if (config != null) {
            config.setReceiptTimeoutCount(0);
        }
    }

    public boolean updateReceipt(String externalSerialNo, Integer receiptStatus, String receiptContent) {
        SmsSendRecord record = sendRecordMapper.selectOne(
                new LambdaQueryWrapper<SmsSendRecord>()
                        .eq(SmsSendRecord::getExternalSerialNo, externalSerialNo)
                        .eq(SmsSendRecord::getDeleted, 0)
                        .last("LIMIT 1")
        );

        if (record == null) {
            log.warn("回执更新失败，未找到发送记录, externalSerialNo={}", externalSerialNo);
            return false;
        }

        if (record.getReceiptStatus() != null && record.getReceiptStatus() != ReceiptStatusEnum.PENDING.getCode()) {
            log.info("回执已处理，跳过, serialNo={}, currentReceiptStatus={}", record.getSerialNo(), record.getReceiptStatus());
            return true;
        }

        LambdaUpdateWrapper<SmsSendRecord> updateWrapper = new LambdaUpdateWrapper<SmsSendRecord>()
                .eq(SmsSendRecord::getId, record.getId())
                .set(SmsSendRecord::getReceiptStatus, receiptStatus)
                .set(SmsSendRecord::getReceiptTime, LocalDateTime.now())
                .set(SmsSendRecord::getReceiptContent, receiptContent);

        if (ReceiptStatusEnum.SUCCESS.getCode().equals(receiptStatus)) {
            updateWrapper.set(SmsSendRecord::getStatus, SendStatusEnum.SUCCESS.getCode());
            recordReceiptSuccess(record.getChannelCode());
        } else if (ReceiptStatusEnum.FAILED.getCode().equals(receiptStatus)) {
            updateWrapper.set(SmsSendRecord::getStatus, SendStatusEnum.FAILED.getCode())
                    .set(SmsSendRecord::getErrorMsg, "回执失败: " + receiptContent);
            recordReceiptSuccess(record.getChannelCode());
        }

        sendRecordMapper.update(null, updateWrapper);

        log.info("回执更新成功, serialNo={}, receiptStatus={}", record.getSerialNo(), receiptStatus);
        return true;
    }

    public boolean updateReceiptBySerialNo(String serialNo, Integer receiptStatus, String receiptContent) {
        SmsSendRecord record = sendRecordMapper.selectOne(
                new LambdaQueryWrapper<SmsSendRecord>()
                        .eq(SmsSendRecord::getSerialNo, serialNo)
                        .eq(SmsSendRecord::getDeleted, 0)
        );

        if (record == null) {
            return false;
        }

        return updateReceipt(record.getExternalSerialNo(), receiptStatus, receiptContent);
    }

    public void initReceiptExpireTime(SmsSendRecord record, Integer channelCode) {
        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);
        if (config != null && config.getReceiptTimeoutSeconds() != null) {
            record.setReceiptExpireTime(LocalDateTime.now().plusSeconds(config.getReceiptTimeoutSeconds()));
        } else {
            record.setReceiptExpireTime(LocalDateTime.now().plusMinutes(5));
        }
        record.setReceiptStatus(ReceiptStatusEnum.PENDING.getCode());
    }

    public int getReceiptTimeoutCount(Integer channelCode) {
        AtomicInteger counter = channelReceiptTimeoutCount.get(channelCode);
        return counter != null ? counter.get() : 0;
    }

    public void resetReceiptTimeoutCount(Integer channelCode) {
        AtomicInteger counter = channelReceiptTimeoutCount.get(channelCode);
        if (counter != null) {
            counter.set(0);
        }
        SmsChannelConfig config = channelManagerService.getChannelConfig(channelCode);
        if (config != null) {
            config.setReceiptTimeoutCount(0);
        }
    }
}
