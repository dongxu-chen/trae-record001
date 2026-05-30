package com.tracing.staining.mq.kafka;

import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import com.tracing.staining.context.TraceHeaderAccessor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.producer.ProducerInterceptor;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.header.Headers;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.Map;

@Slf4j
@Component
public class KafkaTraceProducerInterceptor implements ProducerInterceptor<String, Object> {

    @Override
    public ProducerRecord<String, Object> onSend(ProducerRecord<String, Object> record) {
        StainingContext context = TraceContextHolder.getContext();
        if (context != null) {
            StainingContext childContext = TraceContextHolder.createChildContext();
            Headers headers = record.headers();

            Map<String, String> traceHeaders = TraceHeaderAccessor.toStringHeaders(childContext);
            for (Map.Entry<String, String> entry : traceHeaders.entrySet()) {
                addHeaderIfAbsent(headers, entry.getKey(), entry.getValue());
            }

            log.debug("Kafka message headers injected (message body untouched): topic={}, traceId={}, spanId={}, staining={}",
                    record.topic(), childContext.getTraceId(), childContext.getSpanId(),
                    childContext.getStainingFlag());
        }
        return record;
    }

    @Override
    public void onAcknowledgement(RecordMetadata metadata, Exception exception) {
    }

    @Override
    public void close() {
    }

    @Override
    public void configure(Map<String, ?> configs) {
    }

    private void addHeaderIfAbsent(Headers headers, String key, String value) {
        if (value != null && headers.lastHeader(key) == null) {
            headers.add(key, value.getBytes(StandardCharsets.UTF_8));
        }
    }
}
