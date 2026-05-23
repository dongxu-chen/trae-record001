package com.analytics.pipeline;

import com.analytics.aggregate.MultiDimensionAggregator;
import com.analytics.aggregate.UserBehaviorWindowAggregate;
import com.analytics.config.PipelineConfig;
import com.analytics.config.StateBackendConfig;
import com.analytics.model.MultiDimensionAggregate;
import com.analytics.model.PipelineDynamicConfig;
import com.analytics.model.UserBehaviorAggregate;
import com.analytics.model.UserBehaviorEvent;
import com.analytics.process.BloomFilterDeduplication;
import com.analytics.process.DynamicWindowAggregator;
import com.analytics.process.EventValidationWithMetrics;
import com.analytics.sink.ClickHouseSinkFactory;
import com.analytics.sink.MultiDimensionClickHouseSink;
import com.analytics.source.DynamicConfigSourceFactory;
import com.analytics.source.KafkaSourceFactory;
import com.analytics.util.WatermarkStrategyFactory;
import org.apache.flink.api.common.RuntimeExecutionMode;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.api.java.tuple.Tuple3;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.CheckpointingMode;
import org.apache.flink.streaming.api.datastream.BroadcastStream;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.DataStreamSource;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.CheckpointConfig;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.TimeUnit;

public class UserBehaviorPipeline {

    private static final Logger LOG = LoggerFactory.getLogger(UserBehaviorPipeline.class);

    public static void main(String[] args) throws Exception {
        PipelineConfig config = new PipelineConfig();
        
        Configuration flinkConfig = new Configuration();
        flinkConfig.setString("metrics.reporters", "prom");
        flinkConfig.setString("metrics.reporter.prom.class", "org.apache.flink.metrics.prometheus.PrometheusReporter");
        flinkConfig.setString("metrics.reporter.prom.port", "9250-9260");
        
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment(flinkConfig);

        env.setRuntimeMode(RuntimeExecutionMode.STREAMING);
        env.setParallelism(4);

        configureCheckpoint(env, config);
        env.setStateBackend(StateBackendConfig.createRocksDBStateBackend());
        
        logConfiguration(config);

        DataStreamSource<UserBehaviorEvent> eventStream = env.fromSource(
                KafkaSourceFactory.createKafkaSource(
                        config.getKafkaBrokers(),
                        config.getKafkaTopic(),
                        config.getKafkaGroupId()
                ),
                WatermarkStrategyFactory.createForBoundedOutOfOrderness(),
                "Kafka User Behavior Source"
        );

        String configTopic = System.getenv().getOrDefault("KAFKA_CONFIG_TOPIC", "pipeline_config");
        DataStreamSource<PipelineDynamicConfig> configStream = env.fromSource(
                DynamicConfigSourceFactory.createConfigSource(
                        config.getKafkaBrokers(),
                        configTopic,
                        config.getKafkaGroupId()
                ),
                "Dynamic Config Source"
        );

        BroadcastStream<PipelineDynamicConfig> broadcastConfigStream = configStream
                .broadcast(DynamicWindowAggregator.CONFIG_STATE_DESC);

        SingleOutputStreamOperator<UserBehaviorEvent> validatedStream = eventStream
                .process(new EventValidationWithMetrics())
                .name("Event Validation with Metrics");

        DataStream<UserBehaviorEvent> sideOutputDirtyData = validatedStream
                .getSideOutput(EventValidationWithMetrics.DIRTY_DATA_TAG);
        sideOutputDirtyData.printToErr("Dirty Data: ");

        DataStream<UserBehaviorEvent> deduplicatedStream = validatedStream
                .keyBy(UserBehaviorEvent::getUserId)
                .process(new BloomFilterDeduplication(config))
                .name("BloomFilter Event Deduplication");

        DataStream<UserBehaviorAggregate> dynamicWindowAggregate = deduplicatedStream
                .keyBy(event -> Tuple2.of(event.getUserId(), event.getEventType()))
                .connect(broadcastConfigStream)
                .process(new DynamicWindowAggregator(
                        TimeUnit.MINUTES.toMillis(config.getWindowSizeMin()),
                        TimeUnit.MINUTES.toMillis(config.getAllowedLatenessMin())
                ))
                .name("Dynamic Window Aggregation");

        DataStream<UserBehaviorAggregate> standardAggregate = deduplicatedStream
                .keyBy(event -> Tuple2.of(event.getUserId(), event.getEventType()))
                .window(TumblingEventTimeWindows.of(Time.minutes(config.getWindowSizeMin())))
                .allowedLateness(Time.minutes(config.getAllowedLatenessMin()))
                .process(new UserBehaviorWindowAggregate())
                .name("Standard Window Aggregation");

        DataStream<MultiDimensionAggregate> deviceDimensionAggregate = deduplicatedStream
                .keyBy(MultiDimensionAggregator::extractDeviceKey)
                .window(TumblingEventTimeWindows.of(Time.minutes(config.getWindowSizeMin())))
                .allowedLateness(Time.minutes(config.getAllowedLatenessMin()))
                .aggregate(
                        new MultiDimensionAggregator.MultiDimAggregateFunction(),
                        new MultiDimensionAggregator.MultiDimWindowFunction()
                )
                .name("Device Dimension Aggregation");

        DataStream<MultiDimensionAggregate> channelDimensionAggregate = deduplicatedStream
                .keyBy(MultiDimensionAggregator::extractChannelKey)
                .window(TumblingEventTimeWindows.of(Time.minutes(config.getWindowSizeMin())))
                .allowedLateness(Time.minutes(config.getAllowedLatenessMin()))
                .aggregate(
                        new MultiDimensionAggregator.MultiDimAggregateFunction(),
                        new MultiDimensionAggregator.MultiDimWindowFunction()
                )
                .name("Channel Dimension Aggregation");

        dynamicWindowAggregate
                .addSink(ClickHouseSinkFactory.createClickHouseSink(config))
                .name("ClickHouse Sink - Dynamic Aggregate");

        deviceDimensionAggregate
                .addSink(MultiDimensionClickHouseSink.createSink(config))
                .name("ClickHouse Sink - Device Dimension");

        channelDimensionAggregate
                .addSink(MultiDimensionClickHouseSink.createSink(config))
                .name("ClickHouse Sink - Channel Dimension");

        LOG.info("User Behavior Real-time Analytics Pipeline starting...");
        LOG.info("Prometheus metrics available on port 9250-9260");
        env.execute("User Behavior Real-time Analytics Pipeline");
    }

    private static void configureCheckpoint(StreamExecutionEnvironment env, PipelineConfig config) {
        env.enableCheckpointing(config.getCheckpointIntervalMs());
        
        CheckpointConfig checkpointConfig = env.getCheckpointConfig();
        checkpointConfig.setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);
        checkpointConfig.setMinPauseBetweenCheckpoints(
                Math.max(config.getCheckpointIntervalMs() / 2, TimeUnit.SECONDS.toMillis(30))
        );
        checkpointConfig.setCheckpointTimeout(TimeUnit.MINUTES.toMillis(config.getCheckpointTimeoutMin()));
        checkpointConfig.setMaxConcurrentCheckpoints(1);
        checkpointConfig.setTolerableCheckpointFailureNumber(3);
        checkpointConfig.setExternalizedCheckpointCleanup(
                CheckpointConfig.ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION
        );
        checkpointConfig.enableUnalignedCheckpoints();
        
        LOG.info("Checkpoint configured: interval={}ms, timeout={}min, EXACTLY_ONCE",
                config.getCheckpointIntervalMs(), config.getCheckpointTimeoutMin());
    }

    private static void logConfiguration(PipelineConfig config) {
        LOG.info("Pipeline configuration loaded:");
        LOG.info("  Kafka brokers: {}", config.getKafkaBrokers());
        LOG.info("  Kafka topic: {}", config.getKafkaTopic());
        LOG.info("  Checkpoint interval: {}ms", config.getCheckpointIntervalMs());
        LOG.info("  Window size: {}min", config.getWindowSizeMin());
        LOG.info("  Allowed lateness: {}min", config.getAllowedLatenessMin());
        LOG.info("  BloomFilter expected insertions: {}", config.getBloomFilterExpectedInsertions());
        LOG.info("  BloomFilter FPP: {}", config.getBloomFilterFpp());
    }
}
