package com.tracing.staining.aspect;

import com.tracing.staining.constant.TraceConstant;
import com.tracing.staining.context.StainingContext;
import com.tracing.staining.context.TraceContextHolder;
import com.tracing.staining.context.TraceHeaderAccessor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Aspect
@Component
@Order(1)
public class RabbitTraceAspect {

    @Pointcut("@annotation(org.springframework.amqp.rabbit.annotation.RabbitListener)")
    public void rabbitListenerPointcut() {
    }

    @Pointcut("@annotation(org.springframework.amqp.rabbit.annotation.RabbitHandler)")
    public void rabbitHandlerPointcut() {
    }

    @Around("rabbitListenerPointcut() || rabbitHandlerPointcut()")
    public Object aroundRabbitListener(ProceedingJoinPoint joinPoint) throws Throwable {
        Message message = extractMessage(joinPoint.getArgs());
        boolean hasContext = false;

        try {
            if (message != null) {
                Map<String, String> headers = extractTraceHeaders(message.getMessageProperties());
                if (!headers.isEmpty()) {
                    StainingContext context = TraceContextHolder.createContext(headers);
                    TraceContextHolder.setContext(context);
                    TraceContextHolder.createAndSetOtelSpan("rabbit-consume");
                    hasContext = true;

                    log.debug("RabbitMQ message headers extracted (message body untouched): traceId={}, spanId={}, staining={}",
                            context.getTraceId(), context.getSpanId(), context.getStainingFlag());
                }
            }

            return joinPoint.proceed();

        } finally {
            if (hasContext) {
                try {
                    TraceContextHolder.endOtelSpan();
                } finally {
                    TraceContextHolder.removeContext();
                }
            }
        }
    }

    private Message extractMessage(Object[] args) {
        if (args == null) {
            return null;
        }
        for (Object arg : args) {
            if (arg instanceof Message) {
                return (Message) arg;
            }
        }
        return null;
    }

    private Map<String, String> extractTraceHeaders(MessageProperties properties) {
        Map<String, String> headers = new HashMap<>();
        if (properties == null || properties.getHeaders() == null) {
            return headers;
        }

        Map<String, Object> rawHeaders = properties.getHeaders();
        for (Map.Entry<String, Object> entry : rawHeaders.entrySet()) {
            if (entry.getValue() != null && TraceHeaderAccessor.isTraceHeader(entry.getKey())) {
                headers.put(entry.getKey(), entry.getValue().toString());
            }
        }

        if (properties.getMessageId() != null) {
            headers.putIfAbsent(TraceConstant.REQUEST_ID, properties.getMessageId());
        }

        return headers;
    }
}
