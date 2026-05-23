package com.analytics.process;

import com.analytics.model.PipelineDynamicConfig;
import com.analytics.model.UserBehaviorAggregate;
import com.analytics.model.UserBehaviorEvent;
import org.apache.flink.api.common.state.MapState;
import org.apache.flink.api.common.state.MapStateDescriptor;
import org.apache.flink.api.common.state.ReadOnlyBroadcastState;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.metrics.Counter;
import org.apache.flink.streaming.api.functions.co.KeyedBroadcastProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.math.BigDecimal;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class DynamicWindowAggregator extends KeyedBroadcastProcessFunction<
        Tuple2<String, String>,
        UserBehaviorEvent,
        PipelineDynamicConfig,
        UserBehaviorAggregate> {

    private static final Logger LOG = LoggerFactory.getLogger(DynamicWindowAggregator.class);
    
    public static final MapStateDescriptor<String, PipelineDynamicConfig> CONFIG_STATE_DESC =
            new MapStateDescriptor<>(
                    "dynamic-config",
                    TypeInformation.of(String.class),
                    TypeInformation.of(PipelineDynamicConfig.class)
            );

    private final long defaultWindowSizeMs;
    private final long defaultAllowedLatenessMs;
    
    private transient MapState<Long, WindowAccumulator> windowState;
    private transient Counter lateEventsCounter;
    private transient Counter windowsTriggeredCounter;

    public DynamicWindowAggregator(long defaultWindowSizeMs, long defaultAllowedLatenessMs) {
        this.defaultWindowSizeMs = defaultWindowSizeMs;
        this.defaultAllowedLatenessMs = defaultAllowedLatenessMs;
    }

    @Override
    public void open(Configuration parameters) {
        MapStateDescriptor<Long, WindowAccumulator> windowStateDesc = new MapStateDescriptor<>(
                "window-state",
                Long.class,
                WindowAccumulator.class
        );
        windowState = getRuntimeContext().getMapState(windowStateDesc);
        
        lateEventsCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .counter("late_events");
        
        windowsTriggeredCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("window")
                .counter("windows_triggered");
        
        getRuntimeContext()
                .getMetricGroup()
                .addGroup("window")
                .gauge("active_windows", () -> {
                    try {
                        int count = 0;
                        for (Long key : windowState.keys()) {
                            count++;
                        }
                        return count;
                    } catch (Exception e) {
                        return 0;
                    }
                });
    }

    @Override
    public void processElement(
            UserBehaviorEvent event,
            ReadOnlyContext ctx,
            Collector<UserBehaviorAggregate> out) throws Exception {

        ReadOnlyBroadcastState<String, PipelineDynamicConfig> broadcastState = 
                ctx.getBroadcastState(CONFIG_STATE_DESC);

        long windowSizeMs = defaultWindowSizeMs;
        long allowedLatenessMs = defaultAllowedLatenessMs;
        PipelineDynamicConfig config = broadcastState.get("current");
        if (config != null) {
            windowSizeMs = config.getWindowSizeMs() > 0 ? config.getWindowSizeMs() : defaultWindowSizeMs;
            allowedLatenessMs = config.getAllowedLatenessMs() > 0 ? config.getAllowedLatenessMs() : defaultAllowedLatenessMs;
        }

        long eventTime = event.getTimestamp();
        long windowStart = (eventTime / windowSizeMs) * windowSizeMs;
        long windowEnd = windowStart + windowSizeMs;

        Long currentWatermark = ctx.currentWatermark();
        if (currentWatermark != null && eventTime < currentWatermark - allowedLatenessMs) {
            lateEventsCounter.inc();
            LOG.debug("Late event dropped: eventTime={}, watermark={}", eventTime, currentWatermark);
            return;
        }

        WindowAccumulator accumulator = windowState.get(windowStart);
        if (accumulator == null) {
            accumulator = new WindowAccumulator();
            accumulator.windowStart = windowStart;
            accumulator.windowEnd = windowEnd;
        }
        accumulator.addEvent(event);
        windowState.put(windowStart, accumulator);

        if (currentWatermark != null && windowEnd <= currentWatermark) {
            triggerWindow(windowStart, accumulator, out);
            windowState.remove(windowStart);
            windowsTriggeredCounter.inc();
        }
    }

    @Override
    public void processBroadcastElement(
            PipelineDynamicConfig config,
            Context ctx,
            Collector<UserBehaviorAggregate> out) {
        
        if (config != null && config.getConfigId() != null) {
            LOG.info("Received new dynamic config: windowSizeMs={}, version={}",
                    config.getWindowSizeMs(), config.getVersion());
            
            ctx.getBroadcastState(CONFIG_STATE_DESC).put("current", config);
        }
    }

    @Override
    public void onTimer(long timestamp, OnTimerContext ctx, Collector<UserBehaviorAggregate> out) throws Exception {
        List<Long> windowsToRemove = new ArrayList<>();
        
        for (Long windowStart : windowState.keys()) {
            WindowAccumulator accumulator = windowState.get(windowStart);
            if (accumulator != null && accumulator.windowEnd <= timestamp) {
                triggerWindow(windowStart, accumulator, out);
                windowsToRemove.add(windowStart);
                windowsTriggeredCounter.inc();
            }
        }
        
        for (Long windowStart : windowsToRemove) {
            windowState.remove(windowStart);
        }
    }

    private void triggerWindow(long windowStart, WindowAccumulator accumulator, Collector<UserBehaviorAggregate> out) {
        Tuple2<String, String> currentKey = getCurrentKey();
        
        UserBehaviorAggregate aggregate = UserBehaviorAggregate.builder()
                .userId(currentKey.f0)
                .eventType(currentKey.f1)
                .eventCount(accumulator.count)
                .totalAmount(accumulator.totalAmount)
                .windowStart(new Timestamp(accumulator.windowStart))
                .windowEnd(new Timestamp(accumulator.windowEnd))
                .processTime(new Timestamp(System.currentTimeMillis()))
                .build();
        
        out.collect(aggregate);
        
        LOG.debug("Window triggered: userId={}, eventType={}, windowStart={}, count={}",
                currentKey.f0, currentKey.f1, windowStart, accumulator.count);
    }

    public static class WindowAccumulator implements Serializable {
        public long windowStart;
        public long windowEnd;
        public long count = 0;
        public BigDecimal totalAmount = BigDecimal.ZERO;
        public List<Long> eventTimestamps = new ArrayList<>();

        public void addEvent(UserBehaviorEvent event) {
            count++;
            if (event.getAmount() != null) {
                totalAmount = totalAmount.add(event.getAmount());
            }
            eventTimestamps.add(event.getTimestamp());
            eventTimestamps.sort(Comparator.naturalOrder());
        }
    }
}
