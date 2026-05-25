package com.tracking.flink;

import com.alibaba.fastjson2.JSON;
import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.AnomalyAlert;
import com.tracking.common.model.SessionInfo;
import com.tracking.common.model.TrackEvent;
import com.tracking.flink.function.*;
import org.apache.flink.util.OutputTag;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.api.java.utils.ParameterTool;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.ProcessingTimeSessionWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class TrackingFlinkJob {

    private static final Logger LOG = LoggerFactory.getLogger(TrackingFlinkJob.class);

    public static final OutputTag<AnomalyAlert> ANOMALY_ALERT_TAG = new OutputTag<AnomalyAlert>("anomaly-alerts") {};

    public static void main(String[] args) throws Exception {
        final ParameterTool params = ParameterTool.fromArgs(args);

        String kafkaBrokers = params.get("kafka.brokers", "localhost:9092");
        String kafkaConsumerGroup = params.get("kafka.group.id", TrackingConstants.KAFKA_CONSUMER_GROUP_FLINK);
        String redisHost = params.get("redis.host", "localhost");
        int redisPort = params.getInt("redis.port", 6379);
        String redisPassword = params.get("redis.password", "");
        long sessionTimeout = params.getLong("session.timeout.ms", TrackingConstants.SESSION_TIMEOUT_MILLIS);

        final StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.getConfig().setGlobalJobParameters(params);
        env.enableCheckpointing(60000);

        KafkaSource<String> kafkaSource = KafkaSource.<String>builder()
                .setBootstrapServers(kafkaBrokers)
                .setTopics(TrackingConstants.KAFKA_TOPIC_RAW_EVENTS)
                .setGroupId(kafkaConsumerGroup)
                .setStartingOffsets(OffsetsInitializer.latest())
                .setValueOnlyDeserializer(new SimpleStringSchema())
                .build();

        DataStream<String> rawStream = env.fromSource(kafkaSource, WatermarkStrategy.noWatermarks(), "Kafka Source");

        SingleOutputStreamOperator<TrackEvent> parsedStream = rawStream
                .map((MapFunction<String, TrackEvent>) value -> {
                    try {
                        return JSON.parseObject(value, TrackEvent.class);
                    } catch (Exception e) {
                        LOG.warn("Failed to parse event: {}", value, e);
                        return null;
                    }
                })
                .filter(event -> event != null)
                .name("Parse JSON");

        SingleOutputStreamOperator<TrackEvent> cleanedStream = parsedStream
                .process(new DataCleanFunction())
                .name("Data Clean");

        SingleOutputStreamOperator<TrackEvent> userIdentifiedStream = cleanedStream
                .process(new UserIdentifyFunction(redisHost, redisPort, redisPassword))
                .name("User Identify");

        int anomalyWindow = params.getInt("anomaly.window.minutes", TrackingConstants.ANOMALY_WINDOW_MINUTES);
        int anomalyBaseline = params.getInt("anomaly.baseline.minutes", TrackingConstants.ANOMALY_BASELINE_MINUTES);
        SingleOutputStreamOperator<TrackEvent> anomalyDetectedStream = userIdentifiedStream
                .keyBy(event -> "event:" + event.getEventType())
                .process(new AnomalyDetectionFunction(redisHost, redisPort, redisPassword, anomalyWindow, anomalyBaseline))
                .name("Anomaly Detection - By Event Type");

        SingleOutputStreamOperator<TrackEvent> anomalyByPlatformStream = userIdentifiedStream
                .keyBy(event -> "platform:" + event.getPlatform())
                .process(new AnomalyDetectionFunction(redisHost, redisPort, redisPassword, anomalyWindow, anomalyBaseline))
                .name("Anomaly Detection - By Platform");

        SingleOutputStreamOperator<TrackEvent> sessionStream = anomalyDetectedStream
                .keyBy(TrackEvent::getSessionId)
                .process(new SessionAssignerFunction(redisHost, redisPort, redisPassword, sessionTimeout))
                .name("Session Assign");

        KafkaSink<String> cleanedSink = KafkaSink.<String>builder()
                .setBootstrapServers(kafkaBrokers)
                .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                        .setTopic(TrackingConstants.KAFKA_TOPIC_CLEANED_EVENTS)
                        .setValueSerializationSchema(new SimpleStringSchema())
                        .build())
                .build();

        cleanedStream
                .map((MapFunction<TrackEvent, String>) JSON::toJSONString)
                .sinkTo(cleanedSink)
                .name("Kafka Sink - Cleaned Events");

        DataStream<SessionInfo> sessionAggStream = sessionStream
                .keyBy(TrackEvent::getSessionId)
                .window(ProcessingTimeSessionWindows.withGap(Time.milliseconds(sessionTimeout)))
                .aggregate(new SessionAggregateFunction(), new SessionWindowFunction())
                .name("Session Aggregation");

        sessionAggStream
                .addSink(new SessionClickHouseSink(
                        params.get("clickhouse.host", "localhost"),
                        params.getInt("clickhouse.port", 8123),
                        params.get("clickhouse.database", TrackingConstants.CLICKHOUSE_DB),
                        params.get("clickhouse.username", "default"),
                        params.get("clickhouse.password", "")
                ))
                .name("ClickHouse Sink - Sessions");

        sessionStream
                .addSink(new EventClickHouseSink(
                        params.get("clickhouse.host", "localhost"),
                        params.getInt("clickhouse.port", 8123),
                        params.get("clickhouse.database", TrackingConstants.CLICKHOUSE_DB),
                        params.get("clickhouse.username", "default"),
                        params.get("clickhouse.password", "")
                ))
                .name("ClickHouse Sink - Events");

        sessionStream
                .keyBy(TrackEvent::getUserId)
                .process(new UserIdMappingSinkFunction(redisHost, redisPort, redisPassword))
                .name("Redis Sink - User Mapping");

        sessionStream
                .keyBy(event -> event.getUserId() != null ? event.getUserId() : event.getAnonymousId())
                .process(new DeviceBindingSinkFunction(
                        params.get("clickhouse.host", "localhost"),
                        params.getInt("clickhouse.port", 8123),
                        params.get("clickhouse.database", TrackingConstants.CLICKHOUSE_DB),
                        params.get("clickhouse.username", "default"),
                        params.get("clickhouse.password", ""),
                        redisHost, redisPort, redisPassword
                ))
                .name("Sink - Device Binding");

        sessionStream
                .getSideOutput(SessionAssignerFunction.SESSION_STATS_TAG)
                .addSink(new UserSessionStatsSinkFunction(
                        params.get("clickhouse.host", "localhost"),
                        params.getInt("clickhouse.port", 8123),
                        params.get("clickhouse.database", TrackingConstants.CLICKHOUSE_DB),
                        params.get("clickhouse.username", "default"),
                        params.get("clickhouse.password", ""),
                        redisHost, redisPort, redisPassword
                ))
                .name("Sink - User Session Stats");

        KafkaSink<String> anomalyAlertSink = KafkaSink.<String>builder()
                .setBootstrapServers(kafkaBrokers)
                .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                        .setTopic(TrackingConstants.KAFKA_TOPIC_ANOMALY_ALERT)
                        .setValueSerializationSchema(new SimpleStringSchema())
                        .build())
                .build();

        anomalyDetectedStream
                .getSideOutput(ANOMALY_ALERT_TAG)
                .map((MapFunction<AnomalyAlert, String>) JSON::toJSONString)
                .sinkTo(anomalyAlertSink)
                .name("Kafka Sink - Anomaly Alerts");

        anomalyByPlatformStream
                .getSideOutput(ANOMALY_ALERT_TAG)
                .map((MapFunction<AnomalyAlert, String>) JSON::toJSONString)
                .sinkTo(anomalyAlertSink)
                .name("Kafka Sink - Platform Anomaly Alerts");

        LOG.info("Starting Flink Tracking Job...");
        env.execute("User Behavior Tracking Job");
    }
}
