package com.analytics.process;

import com.analytics.model.UserBehaviorEvent;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.metrics.Counter;
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.util.Collector;
import org.apache.flink.util.OutputTag;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class EventValidationWithMetrics extends ProcessFunction<UserBehaviorEvent, UserBehaviorEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(EventValidationWithMetrics.class);
    
    public static final OutputTag<UserBehaviorEvent> DIRTY_DATA_TAG = 
            new OutputTag<UserBehaviorEvent>("dirty-data") {};
    
    public static final OutputTag<UserBehaviorEvent> LATE_DATA_TAG = 
            new OutputTag<UserBehaviorEvent>("late-data") {};

    private transient Counter totalEventsCounter;
    private transient Counter dirtyEventsCounter;
    private transient Counter validEventsCounter;
    private transient Counter duplicateEventsCounter;

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
        
        validEventsCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .counter("valid_events");
        
        duplicateEventsCounter = getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .counter("duplicate_events");
        
        getRuntimeContext()
                .getMetricGroup()
                .addGroup("data_quality")
                .gauge("dirty_data_ratio", () -> {
                    long total = totalEventsCounter.getCount();
                    return total == 0 ? 0.0 : (double) dirtyEventsCounter.getCount() / total;
                });
    }

    @Override
    public void processElement(
            UserBehaviorEvent event,
            Context ctx,
            Collector<UserBehaviorEvent> out) {
        
        totalEventsCounter.inc();
        
        if (!isValidEvent(event)) {
            dirtyEventsCounter.inc();
            ctx.output(DIRTY_DATA_TAG, event);
            LOG.debug("Dirty event detected: {}", event);
            return;
        }
        
        validEventsCounter.inc();
        out.collect(event);
    }

    private boolean isValidEvent(UserBehaviorEvent event) {
        if (event == null) return false;
        if (event.getEventId() == null || event.getEventId().isEmpty()) return false;
        if (event.getUserId() == null || event.getUserId().isEmpty()) return false;
        if (event.getEventType() == null || event.getEventType().isEmpty()) return false;
        if (event.getTimestamp() <= 0) return false;
        return true;
    }

    public void recordDuplicate() {
        duplicateEventsCounter.inc();
    }
}
