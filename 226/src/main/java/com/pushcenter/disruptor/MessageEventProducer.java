package com.pushcenter.disruptor;

import com.lmax.disruptor.RingBuffer;
import com.pushcenter.model.PushMessage;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class MessageEventProducer {

    private final RingBuffer<MessageEvent> ringBuffer;

    public MessageEventProducer(RingBuffer<MessageEvent> ringBuffer) {
        this.ringBuffer = ringBuffer;
    }

    public void onData(PushMessage message) {
        long sequence = ringBuffer.next();
        try {
            MessageEvent event = ringBuffer.get(sequence);
            event.setMessage(message);
        } finally {
            ringBuffer.publish(sequence);
        }
    }

    public boolean tryPublish(PushMessage message) {
        long sequence = -1;
        try {
            sequence = ringBuffer.tryNext();
            MessageEvent event = ringBuffer.get(sequence);
            event.setMessage(message);
            return true;
        } catch (Exception e) {
            log.warn("Ring buffer is full, message dropped: {}", message.getMessageId());
            return false;
        } finally {
            if (sequence != -1) {
                ringBuffer.publish(sequence);
            }
        }
    }
}
