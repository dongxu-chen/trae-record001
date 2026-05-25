package com.riskcontrol.flink.functions;

import com.alibaba.fastjson.JSON;
import com.riskcontrol.common.model.RiskEvent;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AnomalyDetectionProcessFunction extends KeyedProcessFunction<String, String, String> {

    private static final Logger logger = LoggerFactory.getLogger(AnomalyDetectionProcessFunction.class);

    private transient ValueState<Long> eventCountState;
    private transient ValueState<Long> windowStartTimeState;

    private final long windowSizeMs;
    private final int anomalyThreshold;

    public AnomalyDetectionProcessFunction(long windowSizeMs, int anomalyThreshold) {
        this.windowSizeMs = windowSizeMs;
        this.anomalyThreshold = anomalyThreshold;
    }

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<Long> countDescriptor = new ValueStateDescriptor<>(
                "event-count",
                Long.class
        );
        eventCountState = getRuntimeContext().getState(countDescriptor);

        ValueStateDescriptor<Long> windowDescriptor = new ValueStateDescriptor<>(
                "window-start-time",
                Long.class
        );
        windowStartTimeState = getRuntimeContext().getState(windowDescriptor);
    }

    @Override
    public void processElement(String eventJson, Context ctx, Collector<String> out) throws Exception {
        String key = ctx.getCurrentKey();

        try {
            RiskEvent event = JSON.parseObject(eventJson, RiskEvent.class);
            if (event == null) {
                return;
            }

            long currentTime = event.getEventTimestamp() > 0 ?
                    event.getEventTimestamp() : System.currentTimeMillis();

            Long windowStartTime = windowStartTimeState.value();
            if (windowStartTime == null) {
                windowStartTime = currentTime;
                windowStartTimeState.update(windowStartTime);
            }

            if (currentTime - windowStartTime >= windowSizeMs) {
                Long count = eventCountState.value();
                if (count != null && count >= anomalyThreshold) {
                    String alarm = String.format(
                            "{\"type\":\"ANOMALY_EVENT_FREQUENCY\",\"key\":\"%s\"," +
                                    "\"count\":%d,\"windowSizeMs\":%d,\"threshold\":%d," +
                                    "\"timestamp\":%d,\"severity\":\"MEDIUM\"}",
                            key, count, windowSizeMs, anomalyThreshold, currentTime
                    );
                    out.collect(alarm);
                    logger.warn("Anomaly frequency alarm for key {}: {} events in window",
                            key, count);
                }

                eventCountState.clear();
                windowStartTimeState.update(currentTime);
                eventCountState.update(1L);
            } else {
                Long count = eventCountState.value();
                eventCountState.update(count == null ? 1L : count + 1);
            }

        } catch (Exception e) {
            logger.error("Error processing event in anomaly detection: {}", e.getMessage());
        }
    }
}
