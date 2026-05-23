package com.pushcenter.service;

import com.pushcenter.channel.ChannelHandlerFactory;
import com.pushcenter.channel.PushChannelHandler;
import com.pushcenter.enums.MessageStatus;
import com.pushcenter.model.PushMessage;
import com.pushcenter.model.PushResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

@Slf4j
@Service
public class MessageProcessService {

    @Resource
    private ChannelHandlerFactory channelHandlerFactory;

    @Resource
    private RateLimitService rateLimitService;

    @Resource
    private RetryService retryService;

    @Resource
    private MessageStatisticsService statisticsService;

    @Resource
    private ChannelHealthService channelHealthService;

    public void process(PushMessage message) {
        if (message == null) {
            return;
        }

        log.debug("Processing message: {}", message.getMessageId());

        if (!rateLimitService.tryAcquire(message.getChannel())) {
            log.warn("Rate limit exceeded for channel: {}, message: {}", message.getChannel(), message.getMessageId());
            retryService.scheduleRetry(message, PushResult.builder()
                    .messageId(message.getMessageId())
                    .channel(message.getChannel())
                    .success(false)
                    .errorMessage("Rate limit exceeded")
                    .build());
            return;
        }

        PushChannelHandler handler = channelHandlerFactory.getHandler(message.getChannel());
        if (handler == null) {
            log.error("No handler found for channel: {}", message.getChannel());
            return;
        }

        message.setStatus(MessageStatus.SENDING);
        message.setSendTime(System.currentTimeMillis());

        PushResult result = handler.send(message);

        if (result.isSuccess()) {
            message.setStatus(MessageStatus.SUCCESS);
            statisticsService.recordSuccess(message.getChannel());
            channelHealthService.recordSuccess(message.getChannel());
            retryService.deleteRetryState(message.getMessageId());
            log.debug("Message sent successfully: {}", message.getMessageId());
        } else {
            message.setStatus(MessageStatus.FAILED);
            message.setErrorMessage(result.getErrorMessage());
            statisticsService.recordFailure(message.getChannel());
            channelHealthService.recordFailure(message.getChannel());

            retryService.scheduleRetry(message, result);

            log.warn("Message send failed: {}, error: {}", message.getMessageId(), result.getErrorMessage());
        }
    }
}
