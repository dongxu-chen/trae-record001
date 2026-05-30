package com.tracing.staining.mq.kafka;

import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import com.tracing.staining.context.TraceHeaderAccessor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerInterceptor;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.header.Headers;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class KafkaTraceConsumerInterceptor implements ConsumerInterceptor<String, Object> {

    @Override
    public ConsumerRecords<String, Object> onConsume(ConsumerRecords<String, Object> records) {
        records.forEach(record -> {
            try {
                Headers headers = record.headers();
                Map<String, String> contextHeaders = extractTraceHeaders(headers);

                if (!contextHeaders.isEmpty()) {
                    StainingContext context = TraceContextHolder.createContext(contextHeaders);
                    TraceContextHolder.setContext(context);
                    TraceContextHolder.createAndSetOtelSpan("kafka-consume:" + record.topic());

                    log.debug("Kafka message headers extracted (message body untouched): topic={}, partition={}, offset={}, traceId={}, spanId={}",
                            record.topic(), record.partition(), record.offset(),
                            context.getTraceId(), context.getSpanId());
                }
            } catch (Exception e) {
                log.error("Failed to restore trace context from Kafka message headers", e);
            }
        });
        return records;
    }

    @Override
    public void onCommit(Map<TopicPartition, OffsetAndMetadata> offsets) {
        TraceContextHolder.endOtelSpan();
        TraceContextHolder.removeContext();
    }

    @Override
    public void close() {
    }

    @Override
    public void configure(Map<String, ?> configs) {
    }

    private Map<String, String> extractTraceHeaders(Headers headers) {
        Map<String, String> headerMap = new HashMap<>();
        for (Header header : headers) {
            if (TraceHeaderAccessor.isTraceHeader(header.key())) {
                String value = new String(header.value(), StandardCharsets.UTF_8);
                headerMap.put(header.key(), value);
            }
        }
        return headerMap;
    }
}
