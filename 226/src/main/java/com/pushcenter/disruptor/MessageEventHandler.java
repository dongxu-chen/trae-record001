package com.pushcenter.disruptor;

import com.lmax.disruptor.WorkHandler;
import com.pushcenter.model.PushMessage;
import com.pushcenter.service.MessageProcessService;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class MessageEventHandler implements WorkHandler<MessageEvent> {

    private final MessageProcessService messageProcessService;
    private final int handlerIndex;
    private final int totalHandlers;

    public MessageEventHandler(MessageProcessService messageProcessService, int handlerIndex, int totalHandlers) {
        this.messageProcessService = messageProcessService;
        this.handlerIndex = handlerIndex;
        this.totalHandlers = totalHandlers;
    }

    @Override
    public void onEvent(MessageEvent event) throws Exception {
        PushMessage message = event.getMessage();
        if (message == null) {
            return;
        }

        try {
            if (shouldProcess(message)) {
                messageProcessService.process(message);
            }
        } finally {
            event.clear();
        }
    }

    private boolean shouldProcess(PushMessage message) {
        int hashCode = message.getMessageId().hashCode();
        int targetIndex = Math.abs(hashCode % totalHandlers);
        return targetIndex == handlerIndex;
    }
}
