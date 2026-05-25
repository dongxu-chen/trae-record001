package com.riskcontrol.flink.functions;

import com.riskcontrol.common.model.RiskEvent;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.java.tuple.Tuple2;

public class LoginFrequencyFunction implements AggregateFunction<RiskEvent, Tuple2<String, Integer>, Tuple2<String, Integer>> {

    @Override
    public Tuple2<String, Integer> createAccumulator() {
        return new Tuple2<>("", 0);
    }

    @Override
    public Tuple2<String, Integer> add(RiskEvent event, Tuple2<String, Integer> accumulator) {
        return new Tuple2<>(event.getUserId(), accumulator.f1 + 1);
    }

    @Override
    public Tuple2<String, Integer> getResult(Tuple2<String, Integer> accumulator) {
        return accumulator;
    }

    @Override
    public Tuple2<String, Integer> merge(Tuple2<String, Integer> a, Tuple2<String, Integer> b) {
        return new Tuple2<>(a.f0, a.f1 + b.f1);
    }
}
