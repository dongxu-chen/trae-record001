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

public class IpChangeDetectionFunction extends KeyedProcessFunction<String, RiskEvent, String> {

    private static final Logger logger = LoggerFactory.getLogger(IpChangeDetectionFunction.class);

    private transient ValueState<Set<String>> ipAddressesState;
    private transient ValueState<Long> lastAlertTimeState;

    private final int windowMinutes;
    private final int maxIpChanges;
    private final long alertCooldownMs;

    public IpChangeDetectionFunction(int windowMinutes, int maxIpChanges, long alertCooldownMs) {
        this.windowMinutes = windowMinutes;
        this.maxIpChanges = maxIpChanges;
        this.alertCooldownMs = alertCooldownMs;
    }

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<Set<String>> ipDescriptor = new ValueStateDescriptor<>(
                "ip-addresses",
                org.apache.flink.api.common.typeinfo.TypeInformation.of(
                        org.apache.flink.api.java.typeutils.GenericTypeInfo.of(Set.class)
                )
        );
        ipAddressesState = getRuntimeContext().getState(ipDescriptor);

        ValueStateDescriptor<Long> alertDescriptor = new ValueStateDescriptor<>(
                "last-alert-time",
                Long.class
        );
        lastAlertTimeState = getRuntimeContext().getState(alertDescriptor);
    }

    @Override
    public void processElement(RiskEvent event, Context ctx, Collector<String> out) throws Exception {
        String userId = ctx.getCurrentKey();
        long currentTime = ctx.timestamp();

        Set<String> ipAddresses = ipAddressesState.value();
        if (ipAddresses == null) {
            ipAddresses = new HashSet<>();
        }

        ipAddresses.add(event.getIpAddress());
        ipAddressesState.update(ipAddresses);

        long lastAlertTime = lastAlertTimeState.value() != null ?
                lastAlertTimeState.value() : 0L;

        if (ipAddresses.size() >= maxIpChanges &&
                (currentTime - lastAlertTime) > alertCooldownMs) {

            String alarm = String.format(
                    "{\"type\":\"IP_CHANGE_DETECTION\",\"userId\":\"%s\"," +
                            "\"ipCount\":%d,\"windowMinutes\":%d,\"timestamp\":%d," +
                            "\"ips\":%s,\"severity\":\"HIGH\"}",
                    userId, ipAddresses.size(), windowMinutes,
                    currentTime, ipAddresses
            );

            out.collect(alarm);
            lastAlertTimeState.update(currentTime);
            logger.warn("IP change alarm for user {}: {} IPs in {} minutes",
                    userId, ipAddresses.size(), windowMinutes);

            ipAddresses.clear();
            ipAddressesState.update(ipAddresses);
        }

        ctx.timerService().registerEventTimeTimer(currentTime + windowMinutes * 60 * 1000L);
    }

    @Override
    public void onTimer(long timestamp, OnTimerContext ctx, Collector<String> out) throws Exception {
        ipAddressesState.clear();
    }
}
