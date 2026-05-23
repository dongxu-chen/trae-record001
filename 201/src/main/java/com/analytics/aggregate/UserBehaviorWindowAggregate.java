package com.analytics.aggregate;

import com.analytics.model.UserBehaviorAggregate;
import com.analytics.model.UserBehaviorEvent;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;

import java.math.BigDecimal;
import java.sql.Timestamp;

public class UserBehaviorWindowAggregate 
        extends ProcessWindowFunction<UserBehaviorEvent, UserBehaviorAggregate, Tuple2<String, String>, TimeWindow> {

    @Override
    public void process(
            Tuple2<String, String> key,
            Context context,
            Iterable<UserBehaviorEvent> elements,
            Collector<UserBehaviorAggregate> out) {

        String userId = key.f0;
        String eventType = key.f1;
        
        long count = 0;
        BigDecimal totalAmount = BigDecimal.ZERO;
        
        for (UserBehaviorEvent event : elements) {
            count++;
            if (event.getAmount() != null) {
                totalAmount = totalAmount.add(event.getAmount());
            }
        }
        
        TimeWindow window = context.window();
        
        UserBehaviorAggregate aggregate = UserBehaviorAggregate.builder()
                .userId(userId)
                .eventType(eventType)
                .eventCount(count)
                .totalAmount(totalAmount)
                .windowStart(new Timestamp(window.getStart()))
                .windowEnd(new Timestamp(window.getEnd()))
                .processTime(new Timestamp(System.currentTimeMillis()))
                .build();
        
        out.collect(aggregate);
    }
}
