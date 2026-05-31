package com.datacheck.messagequeue;

import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.util.Properties;

@Slf4j
@Service
@ConditionalOnProperty(name = "message-queue.type", havingValue = "kafka", matchIfMissing = true)
public class KafkaProducerService {

    @Value("${message-queue.kafka.bootstrap-servers:localhost:9092}")
    private String bootstrapServers;

    @Value("${message-queue.kafka.topic:data-sync-topic}")
    private String topic;

    @Value("${message-queue.kafka.producer.acks:all}")
    private String acks;

    @Value("${message-queue.kafka.producer.retries:3}")
    private int retries;

    @Value("${message-queue.kafka.producer.batch-size:16384}")
    private int batchSize;

    @Value("${message-queue.kafka.producer.linger-ms:1}")
    private int lingerMs;

    @Value("${message-queue.kafka.producer.buffer-memory:33554432}")
    private long bufferMemory;

    private KafkaProducer<String, String> producer;

    @PostConstruct
    public void init() {
        try {
            Properties props = new Properties();
            props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
            props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
            props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
            props.put(ProducerConfig.ACKS_CONFIG, acks);
            props.put(ProducerConfig.RETRIES_CONFIG, retries);
            props.put(ProducerConfig.BATCH_SIZE_CONFIG, batchSize);
            props.put(ProducerConfig.LINGER_MS_CONFIG, lingerMs);
            props.put(ProducerConfig.BUFFER_MEMORY_CONFIG, bufferMemory);

            producer = new KafkaProducer<>(props);
            log.info("Kafka producer initialized, bootstrap servers: {}", bootstrapServers);
        } catch (Exception e) {
            log.warn("Failed to initialize Kafka producer, will use fallback mode", e);
        }
    }

    public void send(String message) {
        if (producer == null) {
            log.debug("Kafka producer not available, skipping message: {}", message);
            return;
        }
        try {
            ProducerRecord<String, String> record = new ProducerRecord<>(topic, message);
            producer.send(record, (metadata, exception) -> {
                if (exception != null) {
                    log.error("Failed to send Kafka message", exception);
                } else {
                    log.debug("Kafka message sent successfully, partition: {}, offset: {}",
                            metadata.partition(), metadata.offset());
                }
            });
        } catch (Exception e) {
            log.error("Error sending Kafka message", e);
        }
    }

    @PreDestroy
    public void destroy() {
        if (producer != null) {
            producer.close();
            log.info("Kafka producer closed");
        }
    }
}
