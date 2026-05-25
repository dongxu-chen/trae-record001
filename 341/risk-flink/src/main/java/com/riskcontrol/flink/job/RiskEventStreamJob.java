package com.riskcontrol.flink.job;

import com.alibaba.fastjson.JSON;
import com.riskcontrol.common.model.RiskEvent;
import com.riskcontrol.flink.config.FlinkConfig;
import com.riskcontrol.flink.functions.AnomalyDetectionProcessFunction;
import com.riskcontrol.flink.functions.DeviceSharingDetectionFunction;
import com.riskcontrol.flink.functions.IpChangeDetectionFunction;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.SlidingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaProducer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class RiskEventStreamJob {

    private static final Logger logger = LoggerFactory.getLogger(RiskEventStreamJob.class);

    private final FlinkConfig flinkConfig;
    private final FlinkKafkaConsumer<String> eventConsumer;
    private final FlinkKafkaProducer<String> alarmProducer;

    @Autowired
    public RiskEventStreamJob(FlinkConfig flinkConfig,
                              FlinkKafkaConsumer<String> eventConsumer,
                              FlinkKafkaProducer<String> alarmProducer) {
        this.flinkConfig = flinkConfig;
        this.eventConsumer = eventConsumer;
        this.alarmProducer = alarmProducer;
    }

    public void run() throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(flinkConfig.getParallelism());
        env.enableCheckpointing(flinkConfig.getCheckpointInterval());
        env.getConfig().setAutoWatermarkInterval(5000);

        DataStream<String> eventStream = env.addSource(eventConsumer)
                .name("Kafka-Risk-Events-Source");

        SingleOutputStreamOperator<RiskEvent> parsedEvents = eventStream
                .map(this::parseEvent)
                .filter(event -> event != null && event.getUserId() != null)
                .assignTimestampsAndWatermarks(
                        org.apache.flink.api.common.eventtime.WatermarkStrategy
                                .<RiskEvent>forBoundedOutOfOrderness(java.time.Duration.ofSeconds(30))
                                .withTimestampAssigner((event, timestamp) ->
                                        event.getEventTimestamp() > 0 ? event.getEventTimestamp() : System.currentTimeMillis())
                )
                .name("Parse-Risk-Events");

        DataStream<String> ipChangeAlarms = parsedEvents
                .keyBy(RiskEvent::getUserId)
                .process(new IpChangeDetectionFunction(10, 3, 300000))
                .name("IP-Change-Detection");

        DataStream<String> deviceSharingAlarms = parsedEvents
                .filter(event -> event.getDeviceFingerprint() != null &&
                        event.getDeviceFingerprint().getDeviceId() != null)
                .keyBy(event -> event.getDeviceFingerprint().getDeviceId())
                .process(new DeviceSharingDetectionFunction(24, 5, 600000))
                .name("Device-Sharing-Detection");

        DataStream<String> frequencyAlarms = parsedEvents
                .keyBy(RiskEvent::getUserId)
                .window(SlidingEventTimeWindows.of(Time.minutes(5), Time.minutes(1)))
                .aggregate(new com.riskcontrol.flink.functions.LoginFrequencyFunction())
                .filter(result -> result.f1 >= 10)
                .map(result -> String.format(
                        "{\"type\":\"LOGIN_FREQUENCY_ALARM\",\"userId\":\"%s\"," +
                                "\"loginCount\":%d,\"windowMinutes\":5,\"timestamp\":%d," +
                                "\"severity\":\"HIGH\"}",
                        result.f0, result.f1, System.currentTimeMillis()
                ))
                .name("Login-Frequency-Detection");

        DataStream<String> anomalyAlarms = eventStream
                .keyBy(event -> "global")
                .process(new AnomalyDetectionProcessFunction(60000, 1000))
                .name("Global-Anomaly-Detection");

        DataStream<String> allAlarms = ipChangeAlarms
                .union(deviceSharingAlarms, frequencyAlarms, anomalyAlarms);

        allAlarms.addSink(alarmProducer)
                .name("Kafka-Risk-Alarms-Sink");

        allAlarms.print().name("Alarm-Print-Sink");

        logger.info("Starting Risk Event Stream Processing Job...");
        env.execute("Risk-Control-Stream-Job");
    }

    private RiskEvent parseEvent(String json) {
        try {
            return JSON.parseObject(json, RiskEvent.class);
        } catch (Exception e) {
            logger.warn("Failed to parse event JSON: {}", json, e);
            return null;
        }
    }
}
