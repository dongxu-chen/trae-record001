package com.analytics.metrics;

import org.apache.flink.api.common.time.Time;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.metrics.Counter;
import org.apache.flink.metrics.Gauge;
import org.apache.flink.metrics.Meter;
import org.apache.flink.metrics.MeterView;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.util.Collector;

public class DataQualityMetrics extends ProcessFunction<Object, Object> {

    private transient Counter totalEventsCounter;
    private transient Counter dirtyEventsCounter;
    private transient Counter lateEventsCounter;
    private transient Counter validEventsCounter;
    private transient Counter duplicateEventsCounter;
    
    private transient Meter eventsPerSecond;
    private transient Meter dirtyEventsPerSecond;
    private transient Meter lateEventsPerSecond;
    
    private transient volatile long windowStartTime;
    private transient volatile long windowDirtyCount;
    private transient volatile long windowTotalCount;

    @Override
    public void open(Configuration parameters) {
        totalEventsCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .counter("total_events");
        
        dirtyEventsCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .counter("dirty_events");
        
        lateEventsCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .counter("late_events");
        
        validEventsCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .counter("valid_events");
        
        duplicateEventsCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .counter("duplicate_events");
        
        eventsPerSecond = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .meter("events_per_second", new MeterView(totalEventsCounter, 60));
        
        dirtyEventsPerSecond = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .meter("dirty_events_per_second", new MeterView(dirtyEventsCounter, 60));
        
        lateEventsPerSecond = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .meter("late_events_per_second", new MeterView(lateEventsCounter, 60));
        
        getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .gauge("dirty_data_ratio", new Gauge<Double>() {
                    @Override
                    public Double getValue() {
                        long total = totalEventsCounter.getCount();
                        if (total == 0) return 0.0;
                        return (double) dirtyEventsCounter.getCount() / total;
                    }
                });
        
        getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .gauge("late_data_ratio", new Gauge<Double>() {
                    @Override
                    public Double getValue() {
                        long total = totalEventsCounter.getCount();
                        if (total == 0) return 0.0;
                        return (double) lateEventsCounter.getCount() / total;
                    }
                });
        
        windowStartTime = System.currentTimeMillis();
        windowDirtyCount = 0;
        windowTotalCount = 0;
    }

    @Override
    public void processElement(Object value, Context ctx, Collector<Object> out) {
    }

    public static class MetricsRecorder {
        private final Counter totalEventsCounter;
        private final Counter dirtyEventsCounter;
        private final Counter lateEventsCounter;
        private final Counter validEventsCounter;
        private final Counter duplicateEventsCounter;

        public MetricsRecorder(
                Counter totalEventsCounter,
                Counter dirtyEventsCounter,
                Counter lateEventsCounter,
                Counter validEventsCounter,
                Counter duplicateEventsCounter) {
            this.totalEventsCounter = totalEventsCounter;
            this.dirtyEventsCounter = dirtyEventsCounter;
            this.lateEventsCounter = lateEventsCounter;
            this.validEventsCounter = validEventsCounter;
            this.duplicateEventsCounter = duplicateEventsCounter;
        }

        public void recordTotal() { totalEventsCounter.inc(); }
        public void recordDirty() { dirtyEventsCounter.inc(); }
        public void recordLate() { lateEventsCounter.inc(); }
        public void recordValid() { validEventsCounter.inc(); }
        public void recordDuplicate() { duplicateEventsCounter.inc(); }
    }
}
