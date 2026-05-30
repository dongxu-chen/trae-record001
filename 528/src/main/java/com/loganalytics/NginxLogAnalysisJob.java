package com.loganalytics;

import com.loganalytics.aggregate.MetricsAggregateFunction;
import com.loganalytics.config.FlinkConfig;
import com.loganalytics.functions.CustomMetricCalculator;
import com.loganalytics.functions.DimensionExtractor;
import com.loganalytics.functions.MetricsResultWindowFunction;
import com.loganalytics.functions.SlowRequestTracker;
import com.loganalytics.functions.ThreeSigmaAnomalyDetector;
import com.loganalytics.functions.TrafficForecaster;
import com.loganalytics.model.AlertEvent;
import com.loganalytics.model.CustomMetric;
import com.loganalytics.model.MetricsResult;
import com.loganalytics.model.NginxLogEvent;
import com.loganalytics.model.SlowRequestEvent;
import com.loganalytics.model.TrafficForecast;
import com.loganalytics.sink.AlertSink;
import com.loganalytics.sink.ClickHouseSink;
import com.loganalytics.sink.CustomMetricClickHouseSink;
import com.loganalytics.sink.CustomMetricRedisSink;
import com.loganalytics.sink.ForecastClickHouseSink;
import com.loganalytics.sink.ForecastRedisSink;
import com.loganalytics.sink.RedisSink;
import com.loganalytics.sink.SlowRequestClickHouseSink;
import com.loganalytics.sink.SlowRequestRedisSink;
import com.loganalytics.source.KafkaSourceFactory;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.SingleOutputStreamOperator;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.SlidingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class NginxLogAnalysisJob {
    private static final Logger LOG = LoggerFactory.getLogger(NginxLogAnalysisJob.class);

    public static void main(String[] args) throws Exception {
        LOG.info("Starting Nginx Log Analysis Job v3.0 (T-Digest + 3-Sigma + SlowTrace + Forecast + CustomMetrics)...");

        FlinkConfig config = FlinkConfig.fromEnv();
        LOG.info("Configuration loaded: windowSize={}s, slideSize={}s, tDigestCompression={}, sigma={}, historySize={}",
                config.getWindowSizeSeconds(), config.getSlideSizeSeconds(),
                config.gettDigestCompression(), config.getSigmaMultiplier(), config.getHistoryWindowSize());
        LOG.info("Slow request: threshold={}ms, upstreamRatio={}, profileSize={}",
                config.getSlowRequestThresholdMs(), config.getUpstreamRatioThreshold(), config.getSlowRequestProfileSize());
        LOG.info("Forecast: historySize={}, minConfidence={}",
                config.getForecastHistorySize(), config.getForecastMinConfidence());
        LOG.info("Custom metrics: {}", config.getCustomMetricDefinitions());
        LOG.info("Enabled dimensions: {}", config.getEnabledDimensions());

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        env.enableCheckpointing(60000);

        DataStream<NginxLogEvent> logStream = KafkaSourceFactory.createNginxLogSource(env, config)
                .filter(event -> event != null)
                .assignTimestampsAndWatermarks(
                        WatermarkStrategy.<NginxLogEvent>forMonotonousTimestamps()
                                .withTimestampAssigner((event, timestamp) -> event.getTimestamp())
                );

        DimensionExtractor dimensionExtractor = new DimensionExtractor.Builder()
                .enableAll()
                .enableApi()
                .enableStatus()
                .enableApiStatus()
                .enableApiMethod()
                .enableMethod()
                .enableHost()
                .withApiWhitelist(config.getApiWhitelist())
                .build();

        SingleOutputStreamOperator<Tuple2<String, NginxLogEvent>> dimensionStream = logStream
                .flatMap(dimensionExtractor)
                .name("dimension-extractor");

        SingleOutputStreamOperator<MetricsResult> metricsStream = dimensionStream
                .keyBy(tuple -> tuple.f0)
                .window(SlidingEventTimeWindows.of(
                        Time.seconds(config.getWindowSizeSeconds()),
                        Time.seconds(config.getSlideSizeSeconds())
                ))
                .aggregate(
                        new MetricsAggregateFunction(config.gettDigestCompression()),
                        new MetricsResultWindowFunction(config.getHistoryWindowSize())
                )
                .name("metrics-aggregator");

        metricsStream.print().name("print-metrics");

        metricsStream.addSink(new RedisSink(config))
                .name("redis-sink")
                .setParallelism(2);

        metricsStream.addSink(new ClickHouseSink(config))
                .name("clickhouse-sink")
                .setParallelism(2);

        DataStream<AlertEvent> alertStream = metricsStream
                .flatMap(new ThreeSigmaAnomalyDetector(config.getSigmaMultiplier(), config.getHistoryWindowSize()))
                .name("3sigma-anomaly-detector");

        alertStream.addSink(new AlertSink())
                .name("alert-sink");

        DataStream<SlowRequestEvent> slowRequestStream = logStream
                .keyBy(event -> "api:" + event.getPath())
                .process(new SlowRequestTracker(
                        config.getSlowRequestThresholdMs(),
                        config.getUpstreamRatioThreshold(),
                        config.getSlowRequestProfileSize()
                ))
                .name("slow-request-tracker");

        slowRequestStream.print().name("print-slow-requests");
        slowRequestStream.addSink(new SlowRequestRedisSink(config))
                .name("slow-request-redis-sink")
                .setParallelism(2);
        slowRequestStream.addSink(new SlowRequestClickHouseSink(config))
                .name("slow-request-clickhouse-sink")
                .setParallelism(2);

        DataStream<TrafficForecast> forecastStream = metricsStream
                .keyBy(metrics -> metrics.getDimension() + ":" + metrics.getValue())
                .process(new TrafficForecaster(
                        config.getForecastHistorySize(),
                        config.getForecastMinConfidence()
                ))
                .name("traffic-forecaster");

        forecastStream.print().name("print-forecast");
        forecastStream.addSink(new ForecastRedisSink(config))
                .name("forecast-redis-sink")
                .setParallelism(2);
        forecastStream.addSink(new ForecastClickHouseSink(config))
                .name("forecast-clickhouse-sink")
                .setParallelism(2);

        DataStream<CustomMetric> customMetricStream = metricsStream
                .flatMap(new CustomMetricCalculator(
                        CustomMetricCalculator.parseDefinitions(config.getCustomMetricDefinitions())
                ))
                .name("custom-metric-calculator");

        customMetricStream.print().name("print-custom-metrics");
        customMetricStream.addSink(new CustomMetricRedisSink(config))
                .name("custom-metric-redis-sink")
                .setParallelism(2);
        customMetricStream.addSink(new CustomMetricClickHouseSink(config))
                .name("custom-metric-clickhouse-sink")
                .setParallelism(2);

        LOG.info("Job submission complete. Starting execution...");
        env.execute("Nginx Log Real-time Analysis Job v3.0");
    }
}
