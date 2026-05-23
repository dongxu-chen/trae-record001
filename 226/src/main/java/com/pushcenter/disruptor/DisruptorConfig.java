package com.pushcenter.disruptor;

import com.lmax.disruptor.BlockingWaitStrategy;
import com.lmax.disruptor.RingBuffer;
import com.lmax.disruptor.dsl.Disruptor;
import com.lmax.disruptor.dsl.ProducerType;
import com.pushcenter.service.MessageProcessService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.annotation.Resource;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Slf4j
@Configuration
public class DisruptorConfig {

    @Value("${disruptor.buffer-size: 1048576}")
    private int bufferSize;

    @Value("${disruptor.consumer-threads: 8}")
    private int consumerThreads;

    @Resource
    private MessageProcessService messageProcessService;

    @Bean
    public RingBuffer<MessageEvent> messageEventRingBuffer() {
        ExecutorService executorService = Executors.newFixedThreadPool(consumerThreads);

        MessageEventFactory factory = new MessageEventFactory();

        Disruptor<MessageEvent> disruptor = new Disruptor<>(
                factory,
                bufferSize,
                executorService,
                ProducerType.MULTI,
                new BlockingWaitStrategy()
        );

        MessageEventHandler[] handlers = new MessageEventHandler[consumerThreads];
        for (int i = 0; i < consumerThreads; i++) {
            handlers[i] = new MessageEventHandler(messageProcessService, i, consumerThreads);
        }

        disruptor.handleEventsWithWorkerPool(handlers);

        disruptor.setDefaultExceptionHandler(new MessageEventExceptionHandler());

        disruptor.start();

        log.info("Disruptor started with buffer size: {}, consumer threads: {}", bufferSize, consumerThreads);

        return disruptor.getRingBuffer();
    }

    @Bean
    public MessageEventProducer messageEventProducer(RingBuffer<MessageEvent> ringBuffer) {
        return new MessageEventProducer(ringBuffer);
    }
}
