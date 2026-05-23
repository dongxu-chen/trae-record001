package com.pushcenter.disruptor;

import com.lmax.disruptor.ExceptionHandler;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class MessageEventExceptionHandler implements ExceptionHandler<MessageEvent> {

    @Override
    public void handleEventException(Throwable ex, long sequence, MessageEvent event) {
        log.error("Exception handling event at sequence {}, message: {}",
                sequence,
                event.getMessage() != null ? event.getMessage().getMessageId() : "null",
                ex);
    }

    @Override
    public void handleOnStartException(Throwable ex) {
        log.error("Exception during disruptor start", ex);
    }

    @Override
    public void handleOnShutdownException(Throwable ex) {
        log.error("Exception during disruptor shutdown", ex);
    }
}
