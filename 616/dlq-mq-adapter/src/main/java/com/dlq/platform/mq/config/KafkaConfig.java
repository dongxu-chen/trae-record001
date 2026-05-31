package com.dlq.platform.mq.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.Properties;

@Data
@Configuration
@ConfigurationProperties(prefix = "dlq.mq.kafka")
public class KafkaConfig {

    private String bootstrapServers = "localhost:9092";
    private String groupId = "dlq-consumer-group";
    private String autoOffsetReset = "earliest";
    private boolean enableAutoCommit = false;
    private int autoCommitIntervalMs = 5000;
    private int sessionTimeoutMs = 30000;
    private int maxPollRecords = 500;
    private int pollTimeoutMs = 1000;
    private String keyDeserializer = "org.apache.kafka.common.serialization.StringDeserializer";
    private String valueDeserializer = "org.apache.kafka.common.serialization.StringDeserializer";
    private String keySerializer = "org.apache.kafka.common.serialization.StringSerializer";
    private String valueSerializer = "org.apache.kafka.common.serialization.StringSerializer";
    private String acks = "all";
    private int retries = 3;
    private int batchSize = 16384;
    private int lingerMs = 1;
    private int bufferMemory = 33554432;
    private String deadLetterTopicSuffix = ".dlq";
    private int consumerThreads = 1;

    public Properties buildConsumerProperties() {
        Properties props = new Properties();
        props.put("bootstrap.servers", bootstrapServers);
        props.put("group.id", groupId);
        props.put("auto.offset.reset", autoOffsetReset);
        props.put("enable.auto.commit", String.valueOf(enableAutoCommit));
        props.put("auto.commit.interval.ms", String.valueOf(autoCommitIntervalMs));
        props.put("session.timeout.ms", String.valueOf(sessionTimeoutMs));
        props.put("max.poll.records", String.valueOf(maxPollRecords));
        props.put("key.deserializer", keyDeserializer);
        props.put("value.deserializer", valueDeserializer);
        return props;
    }

    public Properties buildProducerProperties() {
        Properties props = new Properties();
        props.put("bootstrap.servers", bootstrapServers);
        props.put("acks", acks);
        props.put("retries", String.valueOf(retries));
        props.put("batch.size", String.valueOf(batchSize));
        props.put("linger.ms", String.valueOf(lingerMs));
        props.put("buffer.memory", String.valueOf(bufferMemory));
        props.put("key.serializer", keySerializer);
        props.put("value.serializer", valueSerializer);
        return props;
    }
}
