package com.riskcontrol.flink.functions;

import com.riskcontrol.common.model.RiskEvent;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashSet;
import java.util.Set;

public class DeviceSharingDetectionFunction extends KeyedProcessFunction<String, RiskEvent, String> {

    private static final Logger logger = LoggerFactory.getLogger(DeviceSharingDetectionFunction.class);

    private transient ValueState<Set<String>> deviceUsersState;
    private transient ValueState<Long> lastAlertTimeState;

    private final int windowHours;
    private final int maxUsersPerDevice;
    private final long alertCooldownMs;

    public DeviceSharingDetectionFunction(int windowHours, int maxUsersPerDevice, long alertCooldownMs) {
        this.windowHours = windowHours;
        this.maxUsersPerDevice = maxUsersPerDevice;
        this.alertCooldownMs = alertCooldownMs;
    }

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<Set<String>> deviceDescriptor = new ValueStateDescriptor<>(
                "device-users",
                org.apache.flink.api.common.typeinfo.TypeInformation.of(
                        org.apache.flink.api.java.typeutils.GenericTypeInfo.of(Set.class)
                )
        );
        deviceUsersState = getRuntimeContext().getState(deviceDescriptor);

        ValueStateDescriptor<Long> alertDescriptor = new ValueStateDescriptor<>(
                "last-alert-time",
                Long.class
        );
        lastAlertTimeState = getRuntimeContext().getState(alertDescriptor);
    }

    @Override
    public void processElement(RiskEvent event, Context ctx, Collector<String> out) throws Exception {
        String deviceId = ctx.getCurrentKey();
        String userId = event.getUserId();
        long currentTime = ctx.timestamp();

        if (userId == null || deviceId == null) {
            return;
        }

        Set<String> users = deviceUsersState.value();
        if (users == null) {
            users = new HashSet<>();
        }

        users.add(userId);
        deviceUsersState.update(users);

        long lastAlertTime = lastAlertTimeState.value() != null ?
                lastAlertTimeState.value() : 0L;

        if (users.size() >= maxUsersPerDevice &&
                (currentTime - lastAlertTime) > alertCooldownMs) {

            String alarm = String.format(
                    "{\"type\":\"DEVICE_SHARING_DETECTION\",\"deviceId\":\"%s\"," +
                            "\"userCount\":%d,\"windowHours\":%d,\"timestamp\":%d," +
                            "\"users\":%s,\"severity\":\"CRITICAL\"}",
                    deviceId, users.size(), windowHours,
                    currentTime, users
            );

            out.collect(alarm);
            lastAlertTimeState.update(currentTime);
            logger.warn("Device sharing alarm for device {}: {} users in {} hours",
                    deviceId, users.size(), windowHours);
        }

        ctx.timerService().registerEventTimeTimer(currentTime + windowHours * 3600 * 1000L);
    }

    @Override
    public void onTimer(long timestamp, OnTimerContext ctx, Collector<String> out) throws Exception {
        deviceUsersState.clear();
    }
}
