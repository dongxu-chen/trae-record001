package com.log.collector.sink;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flume.*;
import org.apache.flume.conf.Configurable;
import org.apache.flume.sink.AbstractSink;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.*;

public class DeadLetterQueueSink extends AbstractSink implements Configurable {

    private static final Logger logger = LoggerFactory.getLogger(DeadLetterQueueSink.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    private String dlqType;
    private String kafkaBootstrapServers;
    private String kafkaTopic;
    private String localPath;
    private int maxFileSize;
    private int batchSize;

    private KafkaProducer<String, String> kafkaProducer;
    private File currentFile;
    private FileWriter fileWriter;
    private SimpleDateFormat dateFormat;

    @Override
    public void configure(Context context) {
        dlqType = context.getString("sinkType", "local");
        batchSize = context.getInteger("batchSize", 100);

        kafkaBootstrapServers = context.getString("kafka.bootstrap.servers", "localhost:9092");
        kafkaTopic = context.getString("kafka.topic", "dlq_logs");

        localPath = context.getString("local.path", "/data/flume/dlq");
        maxFileSize = context.getInteger("maxFileSize", 104857600);

        dateFormat = new SimpleDateFormat("yyyy-MM-dd");

        logger.info("DeadLetterQueueSink configured - type: {}, batchSize: {}", dlqType, batchSize);
    }

    @Override
    public synchronized void start() {
        logger.info("Starting DeadLetterQueueSink...");

        if ("kafka".equalsIgnoreCase(dlqType)) {
            Properties props = new Properties();
            props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, kafkaBootstrapServers);
            props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,
                    "org.apache.kafka.common.serialization.StringSerializer");
            props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,
                    "org.apache.kafka.common.serialization.StringSerializer");
            props.put(ProducerConfig.ACKS_CONFIG, "all");
            props.put(ProducerConfig.RETRIES_CONFIG, 3);
            props.put(ProducerConfig.BATCH_SIZE_CONFIG, 16384);
            props.put(ProducerConfig.LINGER_MS_CONFIG, 1);

            kafkaProducer = new KafkaProducer<>(props);
            logger.info("Kafka DLQ producer initialized - topic: {}", kafkaTopic);

        } else if ("local".equalsIgnoreCase(dlqType)) {
            File dir = new File(localPath);
            if (!dir.exists()) {
                dir.mkdirs();
            }
            logger.info("Local DLQ path initialized: {}", localPath);
        }

        logger.info("DeadLetterQueueSink started successfully");
        super.start();
    }

    @Override
    public Status process() throws EventDeliveryException {
        Channel channel = getChannel();
        Transaction transaction = channel.getTransaction();
        List<Event> events = new ArrayList<>();

        try {
            transaction.begin();

            for (int i = 0; i < batchSize; i++) {
                Event event = channel.take();
                if (event == null) {
                    break;
                }
                events.add(event);
            }

            if (events.isEmpty()) {
                transaction.commit();
                return Status.BACKOFF;
            }

            processDLQEvents(events);

            transaction.commit();
            logger.debug("Processed {} DLQ events", events.size());
            return Status.READY;

        } catch (Exception e) {
            transaction.rollback();
            logger.error("Failed to process DLQ events", e);
            throw new EventDeliveryException("Failed to process DLQ events", e);
        } finally {
            transaction.close();
        }
    }

    private void processDLQEvents(List<Event> events) throws Exception {
        if ("kafka".equalsIgnoreCase(dlqType)) {
            sendToKafka(events);
        } else if ("local".equalsIgnoreCase(dlqType)) {
            writeToLocal(events);
        }
    }

    private void sendToKafka(List<Event> events) {
        for (Event event : events) {
            try {
                Map<String, Object> dlqMessage = new HashMap<>();
                dlqMessage.put("headers", event.getHeaders());
                dlqMessage.put("body", new String(event.getBody(), StandardCharsets.UTF_8));
                dlqMessage.put("dlq_timestamp", System.currentTimeMillis());

                String key = event.getHeaders().get("offset");
                String value = objectMapper.writeValueAsString(dlqMessage);

                ProducerRecord<String, String> record = new ProducerRecord<>(kafkaTopic, key, value);
                kafkaProducer.send(record, (metadata, exception) -> {
                    if (exception != null) {
                        logger.error("Failed to send DLQ message to Kafka", exception);
                    }
                });

            } catch (Exception e) {
                logger.error("Error preparing DLQ message", e);
            }
        }
        kafkaProducer.flush();
    }

    private void writeToLocal(List<Event> events) throws IOException {
        ensureCurrentFile();

        for (Event event : events) {
            Map<String, Object> dlqMessage = new LinkedHashMap<>();
            dlqMessage.put("timestamp", event.getHeaders().get("timestamp"));
            dlqMessage.put("dlq_reason", event.getHeaders().get("dlq_reason"));
            dlqMessage.put("dlq_sink", event.getHeaders().get("dlq_sink"));
            dlqMessage.put("topic", event.getHeaders().get("topic"));
            dlqMessage.put("partition", event.getHeaders().get("partition"));
            dlqMessage.put("offset", event.getHeaders().get("offset"));
            dlqMessage.put("body", new String(event.getBody(), StandardCharsets.UTF_8));

            String line = objectMapper.writeValueAsString(dlqMessage) + "\n";
            fileWriter.write(line);
        }

        fileWriter.flush();

        if (currentFile.length() >= maxFileSize) {
            rotateFile();
        }
    }

    private void ensureCurrentFile() throws IOException {
        if (currentFile == null || !currentFile.exists()) {
            rotateFile();
        }
    }

    private void rotateFile() throws IOException {
        if (fileWriter != null) {
            fileWriter.close();
        }

        String dateStr = dateFormat.format(new Date());
        File dir = new File(localPath + "/" + dateStr);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        String fileName = "dlq-" + System.currentTimeMillis() + ".log";
        currentFile = new File(dir, fileName);
        fileWriter = new FileWriter(currentFile, true);

        logger.info("Rotated DLQ file: {}", currentFile.getAbsolutePath());
    }

    @Override
    public synchronized void stop() {
        logger.info("Stopping DeadLetterQueueSink...");

        if (kafkaProducer != null) {
            kafkaProducer.close();
        }

        if (fileWriter != null) {
            try {
                fileWriter.close();
            } catch (IOException e) {
                logger.warn("Error closing file writer", e);
            }
        }

        logger.info("DeadLetterQueueSink stopped");
        super.stop();
    }
}
