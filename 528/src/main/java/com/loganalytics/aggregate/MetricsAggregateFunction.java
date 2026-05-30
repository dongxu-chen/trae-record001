package com.loganalytics.aggregate;

import com.loganalytics.model.NginxLogEvent;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.java.tuple.Tuple2;

public class MetricsAggregateFunction implements AggregateFunction<Tuple2<String, NginxLogEvent>, MetricsAccumulator, MetricsAccumulator> {

    private final double compression;

    public MetricsAggregateFunction() {
        this(100.0);
    }

    public MetricsAggregateFunction(double compression) {
        this.compression = compression;
    }

    @Override
    public MetricsAccumulator createAccumulator() {
        return new MetricsAccumulator(compression);
    }

    @Override
    public MetricsAccumulator add(Tuple2<String, NginxLogEvent> tuple, MetricsAccumulator accumulator) {
        NginxLogEvent event = tuple.f1;
        if (event == null) {
            return accumulator;
        }

        double latency = event.getRequestTime() * 1000;
        boolean isError = event.getStatus() >= 400;

        accumulator.add(latency, isError);
        return accumulator;
    }

    @Override
    public MetricsAccumulator getResult(MetricsAccumulator accumulator) {
        return accumulator;
    }

    @Override
    public MetricsAccumulator merge(MetricsAccumulator a, MetricsAccumulator b) {
        a.merge(b);
        return a;
    }
}
