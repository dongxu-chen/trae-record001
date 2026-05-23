package com.analytics.util;

import com.analytics.model.UserBehaviorEvent;
import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;

import java.time.Duration;

public class WatermarkStrategyFactory {

    public static WatermarkStrategy<UserBehaviorEvent> createForBoundedOutOfOrderness() {
        return WatermarkStrategy
                .<UserBehaviorEvent>forBoundedOutOfOrderness(Duration.ofMinutes(5))
                .withTimestampAssigner(new SerializableTimestampAssigner<UserBehaviorEvent>() {
                    @Override
                    public long extractTimestamp(UserBehaviorEvent event, long recordTimestamp) {
                        return event.getTimestamp();
                    }
                });
    }
}
