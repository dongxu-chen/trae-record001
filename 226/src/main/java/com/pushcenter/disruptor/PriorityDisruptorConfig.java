package com.pushcenter.disruptor;

import com.lmax.disruptor.BlockingWaitStrategy;
import com.lmax.disruptor.RingBuffer;
import com.lmax.disruptor.dsl.Disruptor;
import com.lmax.disruptor.dsl.ProducerType;
import com.pushcenter.enums.MessagePriority;
import com.pushcenter.service.MessageProcessService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Slf4j
@Configuration
public class PriorityDisruptorConfig {

    @Value("${disruptor.buffer-size: 1048576}")
    private int bufferSize;

    @Value("${disruptor.consumer-threads: 8}")
    private int consumerThreads;

    @Resource
    private MessageProcessService messageProcessService;

    @Bean
    public Map<MessagePriority, RingBuffer<MessageEvent>> priorityRingBuffers() {
        Map<MessagePriority, RingBuffer<MessageEvent>> ringBuffers = new HashMap<>();

        for (MessagePriority priority : MessagePriority.values()) {
            RingBuffer<MessageEvent> ringBuffer = createDisruptor(priority);
            ringBuffers.put(priority, ringBuffer);
        }

        log.info("Priority Disruptors initialized: {} levels", ringBuffers.size());
        return ringBuffers;
    }

    private RingBuffer<MessageEvent> createDisruptor(MessagePriority priority) {
        ExecutorService executorService = Executors.newFixedThreadPool(
                Math.max(2, consumerThreads / 3));

        MessageEventFactory factory = new MessageEventFactory();

        Disruptor<MessageEvent> disruptor = new Disruptor<>(
                factory,
                bufferSize / 2,
                executorService,
                ProducerType.MULTI,
                new BlockingWaitStrategy()
        );

        MessageEventHandler[] handlers = new MessageEventHandler[Math.max(2, consumerThreads / 3)];
        for (int i = 0; i < handlers.length; i++) {
            handlers[i] = new MessageEventHandler(messageProcessService, i, handlers.length);
        }

        disruptor.handleEventsWithWorkerPool(handlers);
        disruptor.setDefaultExceptionHandler(new MessageEventExceptionHandler());
        disruptor.start();

        log.info("Disruptor started for priority {}: buffer size {}, consumer threads {}",
                priority.getName(), bufferSize / 2, handlers.length);

        return disruptor.getRingBuffer();
    }

    @Bean
    public PriorityMessageProducer priorityMessageProducer(
            Map<MessagePriority, RingBuffer<MessageEvent>> priorityRingBuffers) {
        return new PriorityMessageProducer(priorityRingBuffers);
    }
}
