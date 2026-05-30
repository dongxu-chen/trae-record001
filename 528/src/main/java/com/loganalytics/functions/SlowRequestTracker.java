package com.loganalytics.functions;

import com.loganalytics.model.NginxLogEvent;
import com.loganalytics.model.SlowRequestEvent;
import com.loganalytics.model.TraceSpan;
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

public class SlowRequestTracker extends KeyedProcessFunction<String, NginxLogEvent, SlowRequestEvent> {

    private static final Logger LOG = LoggerFactory.getLogger(SlowRequestTracker.class);

    private final double slowThresholdMs;
    private final double upstreamRatioThreshold;
    private final int recentWindowSize;

    private transient ValueState<LatencyProfile> latencyProfileState;
    private transient AtomicLong traceCounter;

    public SlowRequestTracker(double slowThresholdMs, double upstreamRatioThreshold, int recentWindowSize) {
        this.slowThresholdMs = slowThresholdMs;
        this.upstreamRatioThreshold = upstreamRatioThreshold;
        this.recentWindowSize = recentWindowSize;
    }

    public SlowRequestTracker(double slowThresholdMs) {
        this(slowThresholdMs, 0.7, 100);
    }

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<LatencyProfile> desc = new ValueStateDescriptor<>(
                "latencyProfile", TypeInformation.of(LatencyProfile.class));
        latencyProfileState = getRuntimeContext().getState(desc);
        traceCounter = new AtomicLong(0);
    }

    @Override
    public void processElement(NginxLogEvent event, Context ctx, Collector<SlowRequestEvent> out) throws Exception {
        if (event == null) {
            return;
        }

        LatencyProfile profile = latencyProfileState.value();
        if (profile == null) {
            profile = new LatencyProfile(recentWindowSize);
        }

        profile.add(event.getRequestTime());
        latencyProfileState.update(profile);

        double dynamicThreshold = Math.max(slowThresholdMs, profile.getP99());

        if (event.getRequestTime() >= dynamicThreshold) {
            SlowRequestEvent slowEvent = buildSlowRequestEvent(event, profile, dynamicThreshold);
            out.collect(slowEvent);
        }
    }

    private SlowRequestEvent buildSlowRequestEvent(NginxLogEvent event, LatencyProfile profile, double threshold) {
        double requestTime = event.getRequestTime();
        double upstreamTime = event.getUpstreamResponseTime();
        double selfTime = requestTime - upstreamTime;
        if (selfTime < 0) {
            selfTime = 0;
        }

        boolean isUpstreamSlow = upstreamTime > 0 && (upstreamTime / requestTime) >= upstreamRatioThreshold;
        boolean isSelfSlow = selfTime > 0 && (selfTime / requestTime) >= (1 - upstreamRatioThreshold);

        SlowRequestEvent.SlowReason reason;
        if (isUpstreamSlow && isSelfSlow) {
            reason = SlowRequestEvent.SlowReason.BOTH_SLOW;
        } else if (isUpstreamSlow) {
            reason = SlowRequestEvent.SlowReason.UPSTREAM_SLOW;
        } else if (isSelfSlow) {
            reason = SlowRequestEvent.SlowReason.SELF_SLOW;
        } else {
            reason = SlowRequestEvent.SlowReason.UNKNOWN;
        }

        List<TraceSpan> spans = new ArrayList<>();
        if (upstreamTime > 0) {
            spans.add(TraceSpan.fromUpstream(event.getUpstreamStatus(), upstreamTime));
        }
        if (selfTime > 0) {
            spans.add(TraceSpan.fromSelfProcess(selfTime));
        }

        String traceId = "trace-" + traceCounter.incrementAndGet();

        return SlowRequestEvent.builder()
                .traceId(traceId)
                .dimension("api")
                .value(event.getPath())
                .method(event.getMethod())
                .path(event.getPath())
                .uri(event.getUri())
                .status(event.getStatus())
                .requestTime(requestTime)
                .upstreamResponseTime(upstreamTime)
                .selfProcessTime(selfTime)
                .remoteAddr(event.getRemoteAddr())
                .host(event.getHost())
                .upstreamStatus(event.getUpstreamStatus())
                .downstreamSpans(spans)
                .isUpstreamSlow(isUpstreamSlow)
                .isSelfSlow(isSelfSlow)
                .slowReason(reason.name())
                .timestamp(event.getTimestamp())
                .build();
    }

    public static class LatencyProfile implements java.io.Serializable {
        private final int maxSize;
        private final double[] latencies;
        private int count = 0;
        private int index = 0;
        private double sum = 0.0;

        public LatencyProfile(int maxSize) {
            this.maxSize = maxSize;
            this.latencies = new double[maxSize];
        }

        public void add(double latency) {
            if (count == maxSize) {
                sum -= latencies[index];
            } else {
                count++;
            }
            latencies[index] = latency;
            sum += latency;
            index = (index + 1) % maxSize;
        }

        public double getMean() {
            return count > 0 ? sum / count : 0.0;
        }

        public double getP99() {
            if (count == 0) {
                return 0.0;
            }
            double[] sorted = new double[count];
            for (int i = 0; i < count; i++) {
                sorted[i] = latencies[i];
            }
            java.util.Arrays.sort(sorted);
            int idx = (int) Math.ceil(count * 0.99) - 1;
            return sorted[Math.max(0, Math.min(idx, count - 1))];
        }

        public double getP95() {
            if (count == 0) {
                return 0.0;
            }
            double[] sorted = new double[count];
            for (int i = 0; i < count; i++) {
                sorted[i] = latencies[i];
            }
            java.util.Arrays.sort(sorted);
            int idx = (int) Math.ceil(count * 0.95) - 1;
            return sorted[Math.max(0, Math.min(idx, count - 1))];
        }

        public int getCount() {
            return count;
        }
    }
}
