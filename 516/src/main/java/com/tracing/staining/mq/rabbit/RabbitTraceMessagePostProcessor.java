package com.tracing.staining.mq.rabbit;

import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import com.tracing.staining.context.TraceHeaderAccessor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessagePostProcessor;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.stereotype.Component;

import java.util.Map;

@Slf4j
@Component
public class RabbitTraceMessagePostProcessor implements MessagePostProcessor {

    @Override
    public Message postProcessMessage(Message message) {
        StainingContext context = TraceContextHolder.getContext();
        if (context != null) {
            StainingContext childContext = TraceContextHolder.createChildContext();
            MessageProperties properties = message.getMessageProperties();
            Map<String, Object> headers = properties.getHeaders();

            Map<String, String> traceHeaders = TraceHeaderAccessor.toStringHeaders(childContext);
            for (Map.Entry<String, String> entry : traceHeaders.entrySet()) {
                addHeaderIfAbsent(headers, entry.getKey(), entry.getValue());
            }

            log.debug("RabbitMQ message headers injected (message body untouched): traceId={}, spanId={}, staining={}",
                    childContext.getTraceId(), childContext.getSpanId(), childContext.getStainingFlag());
        }
        return message;
    }

    private void addHeaderIfAbsent(Map<String, Object> headers, String key, String value) {
        if (value != null && !headers.containsKey(key)) {
            headers.put(key, value);
        }
    }
}
