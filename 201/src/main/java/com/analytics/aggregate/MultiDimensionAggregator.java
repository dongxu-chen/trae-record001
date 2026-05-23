package com.analytics.aggregate;

import com.analytics.model.MultiDimensionAggregate;
import com.analytics.model.UserBehaviorEvent;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.java.tuple.Tuple3;
import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;

import java.io.Serializable;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.util.HashSet;
import java.util.Set;

public class MultiDimensionAggregator {

    public static Tuple3<String, String, String> extractDeviceKey(UserBehaviorEvent event) {
        String deviceType = event.getDeviceType() != null ? event.getDeviceType() : "unknown";
        return Tuple3.of("device", deviceType, event.getEventType());
    }

    public static Tuple3<String, String, String> extractChannelKey(UserBehaviorEvent event) {
        String channel = event.getChannel() != null ? event.getChannel() : "unknown";
        return Tuple3.of("channel", channel, event.getEventType());
    }

    public static class MultiDimAccumulator implements Serializable {
        public long eventCount = 0;
        public BigDecimal totalAmount = BigDecimal.ZERO;
        public Set<String> uniqueUsers = new HashSet<>();

        public void add(UserBehaviorEvent event) {
            eventCount++;
            if (event.getAmount() != null) {
                totalAmount = totalAmount.add(event.getAmount());
            }
            uniqueUsers.add(event.getUserId());
        }

        public MultiDimAccumulator merge(MultiDimAccumulator other) {
            this.eventCount += other.eventCount;
            this.totalAmount = this.totalAmount.add(other.totalAmount);
            this.uniqueUsers.addAll(other.uniqueUsers);
            return this;
        }
    }

    public static class MultiDimAggregateFunction 
            implements AggregateFunction<UserBehaviorEvent, MultiDimAccumulator, MultiDimAccumulator> {

        @Override
        public MultiDimAccumulator createAccumulator() {
            return new MultiDimAccumulator();
        }

        @Override
        public MultiDimAccumulator add(UserBehaviorEvent event, MultiDimAccumulator accumulator) {
            accumulator.add(event);
            return accumulator;
        }

        @Override
        public MultiDimAccumulator getResult(MultiDimAccumulator accumulator) {
            return accumulator;
        }

        @Override
        public MultiDimAccumulator merge(MultiDimAccumulator a, MultiDimAccumulator b) {
            return a.merge(b);
        }
    }

    public static class MultiDimWindowFunction 
            extends ProcessWindowFunction<MultiDimAccumulator, MultiDimensionAggregate, Tuple3<String, String, String>, TimeWindow> {

        @Override
        public void process(
                Tuple3<String, String, String> key,
                Context context,
                Iterable<MultiDimAccumulator> elements,
                Collector<MultiDimensionAggregate> out) {

            MultiDimAccumulator acc = elements.iterator().next();
            
            BigDecimal avgAmount = acc.eventCount > 0 
                    ? acc.totalAmount.divide(BigDecimal.valueOf(acc.eventCount), 2, RoundingMode.HALF_UP)
                    : BigDecimal.ZERO;

            MultiDimensionAggregate aggregate = MultiDimensionAggregate.builder()
                    .dimensionType(key.f0)
                    .dimensionValue(key.f1)
                    .eventType(key.f2)
                    .eventCount(acc.eventCount)
                    .uniqueUserCount(acc.uniqueUsers.size())
                    .totalAmount(acc.totalAmount)
                    .avgAmount(avgAmount)
                    .windowStart(new Timestamp(context.window().getStart()))
                    .windowEnd(new Timestamp(context.window().getEnd()))
                    .processTime(new Timestamp(System.currentTimeMillis()))
                    .build();

            out.collect(aggregate);
        }
    }
}
