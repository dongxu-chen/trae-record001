package com.pushcenter.channel;

import com.pushcenter.enums.MessageStatus;
import com.pushcenter.enums.PushChannel;
import com.pushcenter.model.PushMessage;
import com.pushcenter.model.PushResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class WechatWorkChannelHandler implements PushChannelHandler {

    @Override
    public PushChannel getChannel() {
        return PushChannel.WECHAT_WORK;
    }

    @Override
    public PushResult send(PushMessage message) {
        log.info("Sending WeChat Work to: {}, title: {}", message.getReceiver(), message.getTitle());

        PushResult.PushResultBuilder builder = PushResult.builder()
                .messageId(message.getMessageId())
                .channel(PushChannel.WECHAT_WORK)
                .sendTime(System.currentTimeMillis());

        try {
            boolean success = simulateSend(message);

            if (success) {
                builder.status(MessageStatus.SUCCESS)
                        .success(true)
                        .thirdPartyId("wechat_work_" + System.currentTimeMillis());
                log.info("WeChat Work sent successfully: {}", message.getMessageId());
            } else {
                builder.status(MessageStatus.FAILED)
                        .success(false)
                        .errorMessage("WeChat Work service returned failure");
                log.warn("WeChat Work send failed: {}", message.getMessageId());
            }
        } catch (Exception e) {
            builder.status(MessageStatus.FAILED)
                    .success(false)
                    .errorMessage(e.getMessage());
            log.error("WeChat Work send exception: {}", message.getMessageId(), e);
        }

        return builder.build();
    }

    @Override
    public boolean isAvailable() {
        return true;
    }

    private boolean simulateSend(PushMessage message) {
        return Math.random() > 0.1;
    }
}
