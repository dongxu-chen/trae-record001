package com.dlq.platform.mq.consumer.kafka;

import com.dlq.platform.mq.config.KafkaConfig;
import com.dlq.platform.mq.consumer.AbstractMessageConsumer;
import com.dlq.platform.mq.producer.kafka.KafkaProducer;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.common.TopicPartition;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Slf4j
public class KafkaConsumer extends AbstractMessageConsumer {

    private final KafkaConfig config;
    private final KafkaProducer deadLetterProducer;
    private org.apache.kafka.clients.consumer.KafkaConsumer<String, String> consumer;
    private ExecutorService executorService;

    public KafkaConsumer(KafkaConfig config, KafkaProducer deadLetterProducer) {
        this.config = config;
        this.deadLetterProducer = deadLetterProducer;
        initConsumer();
    }

    private void initConsumer() {
        Properties props = config.buildConsumerProperties();
        consumer = new org.apache.kafka.clients.consumer.KafkaConsumer<>(props);
        executorService = Executors.newFixedThreadPool(config.getConsumerThreads());
    }

    @Override
    protected void doSubscribe(String topic) {
        if (consumer != null) {
            List<String> topics = new ArrayList<>(subscribedTopics);
            consumer.subscribe(topics);
        }
    }

    @Override
    protected void doUnsubscribe(String topic) {
        if (consumer != null && !subscribedTopics.isEmpty()) {
            List<String> topics = new ArrayList<>(subscribedTopics);
            consumer.subscribe(topics);
        } else if (consumer != null) {
            consumer.unsubscribe();
        }
    }

    @Override
    protected void doConsume() {
        executorService.submit(this::pollMessages);
    }

    private void pollMessages() {
        try {
            while (isRunning()) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(config.getPollTimeoutMs()));
                for (ConsumerRecord<String, String> record : records) {
                    try {
                        handleMessage(record.topic(), record.value());
                        consumer.commitSync();
                    } catch (Exception e) {
                        log.error("消费消息异常, topic: {}, partition: {}, offset: {}",
                                record.topic(), record.partition(), record.offset(), e);
                        forwardToDeadLetter(record, e);
                        consumer.commitSync();
                    }
                }
            }
        } catch (Exception e) {
            log.error("Kafka消费线程异常", e);
        }
    }

    private void forwardToDeadLetter(ConsumerRecord<String, String> record, Throwable throwable) {
        try {
            String deadLetterTopic = record.topic() + config.getDeadLetterTopicSuffix();
            deadLetterProducer.send(deadLetterTopic, record.value());
            log.info("消息已转发至死信队列, 原topic: {}, 死信topic: {}, message: {}",
                    record.topic(), deadLetterTopic, record.value());
        } catch (Exception ex) {
            log.error("转发死信失败, topic: {}, message: {}", record.topic(), record.value(), ex);
        }
    }

    @Override
    protected void doStop() {
        if (executorService != null) {
            executorService.shutdown();
        }
        if (consumer != null) {
            consumer.close();
        }
    }

    public void seekToBeginning(String topic) {
        if (consumer != null) {
            List<TopicPartition> partitions = new ArrayList<>();
            consumer.partitionsFor(topic).forEach(info ->
                    partitions.add(new TopicPartition(topic, info.partition())));
            consumer.seekToBeginning(partitions);
        }
    }

    public void seekToEnd(String topic) {
        if (consumer != null) {
            List<TopicPartition> partitions = new ArrayList<>();
            consumer.partitionsFor(topic).forEach(info ->
                    partitions.add(new TopicPartition(topic, info.partition())));
            consumer.seekToEnd(partitions);
        }
    }
}
