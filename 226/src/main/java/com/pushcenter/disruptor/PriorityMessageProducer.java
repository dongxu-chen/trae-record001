package com.pushcenter.disruptor;

import com.lmax.disruptor.RingBuffer;
import com.pushcenter.enums.MessagePriority;
import com.pushcenter.model.PushMessage;
import lombok.extern.slf4j.Slf4j;

import java.util.Map;

@Slf4j
public class PriorityMessageProducer {

    private final Map<MessagePriority, RingBuffer<MessageEvent>> ringBuffers;

    public PriorityMessageProducer(Map<MessagePriority, RingBuffer<MessageEvent>> ringBuffers) {
        this.ringBuffers = ringBuffers;
    }

    public boolean publish(PushMessage message) {
        MessagePriority priority = message.getPriority() != null ? message.getPriority() : MessagePriority.NORMAL;

        if (message.isJumpQueue() && priority != MessagePriority.HIGH) {
            log.info("Message {} jumping queue, upgrading to HIGH priority", message.getMessageId());
            priority = MessagePriority.HIGH;
            message.setPriority(MessagePriority.HIGH);
        }

        RingBuffer<MessageEvent> ringBuffer = ringBuffers.get(priority);
        if (ringBuffer == null) {
            log.error("No ring buffer found for priority: {}", priority);
            return false;
        }

        try {
            long sequence = ringBuffer.tryNext();
            try {
                MessageEvent event = ringBuffer.get(sequence);
                event.setMessage(message);
            } finally {
                ringBuffer.publish(sequence);
            }
            return true;
        } catch (Exception e) {
            log.warn("Ring buffer full for priority {}, message dropped: {}",
                    priority, message.getMessageId());
            return false;
        }
    }

    public long getPendingCount(MessagePriority priority) {
        RingBuffer<MessageEvent> ringBuffer = ringBuffers.get(priority);
        if (ringBuffer == null) {
            return 0;
        }
        return ringBuffer.bufferSize() - ringBuffer.remainingCapacity();
    }

    public Map<MessagePriority, Long> getAllPendingCounts() {
        Map<MessagePriority, Long> counts = new java.util.HashMap<>();
        for (Map.Entry<MessagePriority, RingBuffer<MessageEvent>> entry : ringBuffers.entrySet()) {
            RingBuffer<MessageEvent> ringBuffer = entry.getValue();
            long pending = ringBuffer.bufferSize() - ringBuffer.remainingCapacity();
            counts.put(entry.getKey(), pending);
        }
        return counts;
    }
}
