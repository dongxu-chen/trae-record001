package com.riskcontrol.flink.config;

import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaProducer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Properties;

@Configuration
public class FlinkConfig {

    @Value("${riskcontrol.flink.kafka.bootstrap-servers:localhost:9092}")
    private String kafkaBootstrapServers;

    @Value("${riskcontrol.flink.kafka.group-id:risk-control-group}")
    private String kafkaGroupId;

    @Value("${riskcontrol.flink.kafka.event-topic:risk-events}")
    private String eventTopic;

    @Value("${riskcontrol.flink.kafka.alarm-topic:risk-alarms}")
    private String alarmTopic;

    @Value("${riskcontrol.flink.parallelism:4}")
    private int parallelism;

    @Value("${riskcontrol.flink.checkpoint-interval:60000}")
    private long checkpointInterval;

    @Bean
    public Properties flinkKafkaProperties() {
        Properties properties = new Properties();
        properties.setProperty("bootstrap.servers", kafkaBootstrapServers);
        properties.setProperty("group.id", kafkaGroupId);
        properties.setProperty("enable.auto.commit", "false");
        properties.setProperty("auto.offset.reset", "latest");
        properties.setProperty("flink.partition-discovery.interval-millis", "30000");
        return properties;
    }

    @Bean
    public FlinkKafkaConsumer<String> eventConsumer(Properties flinkKafkaProperties) {
        return new FlinkKafkaConsumer<>(
                eventTopic,
                new SimpleStringSchema(),
                flinkKafkaProperties
        );
    }

    @Bean
    public FlinkKafkaProducer<String> alarmProducer(Properties flinkKafkaProperties) {
        return new FlinkKafkaProducer<>(
                alarmTopic,
                new SimpleStringSchema(),
                flinkKafkaProperties
        );
    }

    public String getEventTopic() {
        return eventTopic;
    }

    public String getAlarmTopic() {
        return alarmTopic;
    }

    public int getParallelism() {
        return parallelism;
    }

    public long getCheckpointInterval() {
        return checkpointInterval;
    }
}
