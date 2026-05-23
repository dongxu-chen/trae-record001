package com.pushcenter.channel;

import com.pushcenter.enums.MessageStatus;
import com.pushcenter.enums.PushChannel;
import com.pushcenter.model.PushMessage;
import com.pushcenter.model.PushResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class SmsChannelHandler implements PushChannelHandler {

    @Override
    public PushChannel getChannel() {
        return PushChannel.SMS;
    }

    @Override
    public PushResult send(PushMessage message) {
        log.info("Sending SMS to: {}, content: {}", message.getReceiver(), message.getContent());

        PushResult.PushResultBuilder builder = PushResult.builder()
                .messageId(message.getMessageId())
                .channel(PushChannel.SMS)
                .sendTime(System.currentTimeMillis());

        try {
            boolean success = simulateSend(message);

            if (success) {
                builder.status(MessageStatus.SUCCESS)
                        .success(true)
                        .thirdPartyId("sms_" + System.currentTimeMillis());
                log.info("SMS sent successfully: {}", message.getMessageId());
            } else {
                builder.status(MessageStatus.FAILED)
                        .success(false)
                        .errorMessage("SMS service returned failure");
                log.warn("SMS send failed: {}", message.getMessageId());
            }
        } catch (Exception e) {
            builder.status(MessageStatus.FAILED)
                    .success(false)
                    .errorMessage(e.getMessage());
            log.error("SMS send exception: {}", message.getMessageId(), e);
        }

        return builder.build();
    }

    @Override
    public boolean isAvailable() {
        return true;
    }

    private boolean simulateSend(PushMessage message) {
        return Math.random() > 0.15;
    }
}
