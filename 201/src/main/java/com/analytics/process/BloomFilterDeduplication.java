package com.analytics.process;

import com.analytics.config.PipelineConfig;
import com.analytics.model.UserBehaviorEvent;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.common.time.Time;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;

public class BloomFilterDeduplication 
        extends KeyedProcessFunction<String, UserBehaviorEvent, UserBehaviorEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(BloomFilterDeduplication.class);
    private final PipelineConfig config;
    private transient ValueState<BloomFilterWrapper> bloomFilterState;

    public BloomFilterDeduplication(PipelineConfig config) {
        this.config = config;
    }

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<BloomFilterWrapper> stateDescriptor = new ValueStateDescriptor<>(
                "bloomFilterState",
                BloomFilterWrapper.class
        );
        stateDescriptor.enableTimeToLive(
                org.apache.flink.api.common.state.StateTtlConfig
                        .newBuilder(Time.hours(config.getStateTtlHours()))
                        .setUpdateType(org.apache.flink.api.common.state.StateTtlConfig.UpdateType.OnCreateAndWrite)
                        .setStateVisibility(org.apache.flink.api.common.state.StateTtlConfig.StateVisibility.NeverReturnExpired)
                        .build()
        );
        bloomFilterState = getRuntimeContext().getState(stateDescriptor);
    }

    @Override
    public void processElement(
            UserBehaviorEvent event,
            Context ctx,
            Collector<UserBehaviorEvent> out) throws Exception {

        if (!isValidEvent(event)) {
            return;
        }

        String compositeKey = event.getUserId() + "_" + event.getEventId();
        
        BloomFilterWrapper wrapper = bloomFilterState.value();
        if (wrapper == null) {
            wrapper = new BloomFilterWrapper(
                    config.getBloomFilterExpectedInsertions(),
                    config.getBloomFilterFpp()
            );
        }

        if (!wrapper.mightContain(compositeKey)) {
            wrapper.put(compositeKey);
            bloomFilterState.update(wrapper);
            out.collect(event);
        }
    }

    private boolean isValidEvent(UserBehaviorEvent event) {
        if (event == null) return false;
        if (event.getEventId() == null || event.getEventId().isEmpty()) return false;
        if (event.getUserId() == null || event.getUserId().isEmpty()) return false;
        if (event.getEventType() == null || event.getEventType().isEmpty()) return false;
        if (event.getTimestamp() <= 0) return false;
        return true;
    }

    public static class BloomFilterWrapper implements Serializable {
        private transient org.apache.flink.shaded.guava30.com.google.common.hash.BloomFilter<CharSequence> bloomFilter;
        private int expectedInsertions;
        private double fpp;

        public BloomFilterWrapper() {}

        public BloomFilterWrapper(int expectedInsertions, double fpp) {
            this.expectedInsertions = expectedInsertions;
            this.fpp = fpp;
            initBloomFilter();
        }

        private void initBloomFilter() {
            this.bloomFilter = org.apache.flink.shaded.guava30.com.google.common.hash.BloomFilter.create(
                    org.apache.flink.shaded.guava30.com.google.common.hash.Funnels.stringFunnel(java.nio.charset.StandardCharsets.UTF_8),
                    expectedInsertions,
                    fpp
            );
        }

        public boolean mightContain(String key) {
            return bloomFilter != null && bloomFilter.mightContain(key);
        }

        public void put(String key) {
            if (bloomFilter != null) {
                bloomFilter.put(key);
            }
        }

        private void writeObject(ObjectOutputStream out) throws IOException {
            out.defaultWriteObject();
            if (bloomFilter != null) {
                bloomFilter.writeTo(out);
            }
        }

        private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {
            in.defaultReadObject();
            if (expectedInsertions > 0) {
                bloomFilter = org.apache.flink.shaded.guava30.com.google.common.hash.BloomFilter.readFrom(
                        in,
                        org.apache.flink.shaded.guava30.com.google.common.hash.Funnels.stringFunnel(java.nio.charset.StandardCharsets.UTF_8)
                );
            } else {
                initBloomFilter();
            }
        }
    }
}
