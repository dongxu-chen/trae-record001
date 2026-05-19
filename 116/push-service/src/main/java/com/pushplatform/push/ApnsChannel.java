package com.pushplatform.push;

import com.pushplatform.common.enums.PushChannelEnum;
import com.pushplatform.entity.PushRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.UUID;

@Component
public class ApnsChannel implements PushChannel {

    private static final Logger logger = LoggerFactory.getLogger(ApnsChannel.class);

    @Value("${push.apns.bundle-id:}")
    private String bundleId;

    @Override
    public String getChannel() {
        return PushChannelEnum.APNS.getCode();
    }

    @Override
    public PushResult send(PushRecord record) {
        try {
            logger.info("APNS send message, deviceToken: {}, title: {}, content: {}", 
                    record.getTarget(), record.getTitle(), record.getContent());
            
            String messageId = UUID.randomUUID().toString();
            return PushResult.success(messageId);
        } catch (Exception e) {
            logger.error("APNS send error, deviceToken: {}", record.getTarget(), e);
            return PushResult.fail(e.getMessage());
        }
    }
}
