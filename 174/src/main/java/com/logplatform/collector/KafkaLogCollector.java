package com.logplatform.collector;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.logplatform.config.LogCollectorProperties;
import com.logplatform.model.LogEntry;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "log.collector.kafka", name = "enabled", havingValue = "true")
public class KafkaLogCollector implements LogCollector {

    private final LogCollectorProperties properties;
    private final ObjectMapper objectMapper;
    private final List<KafkaConsumer<String, String>> consumers = new ArrayList<>();
    private final ExecutorService executorService = Executors.newCachedThreadPool();
    private volatile boolean running = false;
    private LogHandler logHandler;

    @Override
    public String getName() {
        return "KafkaLogCollector";
    }

    @PostConstruct
    @Override
    public void start() {
        if (running) return;
        running = true;

        for (LogCollectorProperties.KafkaTopic topic : properties.getKafka().getTopics()) {
            for (int i = 0; i < topic.getConcurrency(); i++) {
                startConsumer(topic);
            }
        }

        log.info("KafkaLogCollector started with {} topics", properties.getKafka().getTopics().size());
    }

    private void startConsumer(LogCollectorProperties.KafkaTopic topic) {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, properties.getKafka().getBootstrapServers());
        props.put(ConsumerConfig.GROUP_ID_CONFIG, topic.getGroupId());
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "true");
        props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 500);

        KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
        consumer.subscribe(Collections.singletonList(topic.getName()));
        consumers.add(consumer);

        executorService.submit(() -> {
            while (running) {
                try {
                    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));
                    for (ConsumerRecord<String, String> record : records) {
                        processRecord(record, topic);
                    }
                } catch (Exception e) {
                    if (running) {
                        log.error("Error consuming from Kafka topic: {}", topic.getName(), e);
                    }
                }
            }
        });
    }

    private void processRecord(ConsumerRecord<String, String> record, LogCollectorProperties.KafkaTopic topic) {
        try {
            LogEntry entry = parseLogEntry(record.value());
            if (entry.getAppName() == null) {
                entry.setAppName(topic.getName());
            }
            if (entry.getTimestamp() == null) {
                entry.setTimestamp(Instant.ofEpochMilli(record.timestamp()));
            }

            if (logHandler != null) {
                logHandler.onLog(entry);
            }
        } catch (Exception e) {
            log.warn("Failed to parse Kafka message: {}", record.value(), e);
        }
    }

    private LogEntry parseLogEntry(String value) {
        LogEntry entry = new LogEntry();
        try {
            JsonNode node = objectMapper.readTree(value);

            if (node.has("@timestamp")) {
                entry.setTimestamp(Instant.parse(node.get("@timestamp").asText()));
            }
            if (node.has("appName")) {
                entry.setAppName(node.get("appName").asText());
            }
            if (node.has("level")) {
                entry.setLevel(node.get("level").asText());
            }
            if (node.has("message")) {
                entry.setMessage(node.get("message").asText());
            }
            if (node.has("logger")) {
                entry.setLogger(node.get("logger").asText());
            }
            if (node.has("thread")) {
                entry.setThread(node.get("thread").asText());
            }
            if (node.has("stackTrace")) {
                entry.setStackTrace(node.get("stackTrace").asText());
            }
            if (node.has("host")) {
                entry.setHost(node.get("host").asText());
            }
            if (node.has("traceId")) {
                entry.setTraceId(node.get("traceId").asText());
            }
        } catch (Exception e) {
            entry.setMessage(value);
        }
        return entry;
    }

    @PreDestroy
    @Override
    public void stop() {
        running = false;
        executorService.shutdown();
        for (KafkaConsumer<String, String> consumer : consumers) {
            try {
                consumer.wakeup();
                consumer.close();
            } catch (Exception e) {
                log.warn("Error closing Kafka consumer", e);
            }
        }
        log.info("KafkaLogCollector stopped");
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    @Override
    public void collect(List<LogEntry> logs) {
    }

    public void setLogHandler(LogHandler handler) {
        this.logHandler = handler;
    }
}
