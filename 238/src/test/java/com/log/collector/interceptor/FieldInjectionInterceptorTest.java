package com.log.collector.interceptor;

import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.event.SimpleEvent;
import org.junit.Before;
import org.junit.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

public class FieldInjectionInterceptorTest {

    private FieldInjectionInterceptor.Builder builder;
    private FieldInjectionInterceptor interceptor;

    @Before
    public void setUp() {
        builder = new FieldInjectionInterceptor.Builder();
        Context context = new Context();
        context.put("fields", "collect_timestamp,hostname,agent_id,topic,ip");
        context.put("agentId", "test-agent-01");
        builder.configure(context);
        interceptor = (FieldInjectionInterceptor) builder.build();
        interceptor.initialize();
    }

    @Test
    public void testFieldInjection() {
        Event event = new SimpleEvent();
        event.setBody("Test log message".getBytes());
        Map<String, String> headers = new HashMap<>();
        headers.put("topic", "test-topic");
        headers.put("partition", "0");
        headers.put("offset", "12345");
        event.setHeaders(headers);

        Event result = interceptor.intercept(event);

        assertNotNull(result);
        assertNotNull(result.getHeaders().get("collect_timestamp"));
        assertNotNull(result.getHeaders().get("hostname"));
        assertEquals("test-agent-01", result.getHeaders().get("agent_id"));
        assertEquals("test-topic", result.getHeaders().get("kafka_topic"));
        assertNotNull(result.getHeaders().get("collector_ip"));
    }

    @Test
    public void testTraceIdInjection() {
        Context context = new Context();
        context.put("fields", "trace_id,span_id,uuid");
        builder = new FieldInjectionInterceptor.Builder();
        builder.configure(context);
        interceptor = (FieldInjectionInterceptor) builder.build();

        Event event = new SimpleEvent();
        event.setBody("Test log".getBytes());
        event.setHeaders(new HashMap<>());

        Event result = interceptor.intercept(event);

        assertNotNull(result.getHeaders().get("trace_id"));
        assertNotNull(result.getHeaders().get("span_id"));
        assertNotNull(result.getHeaders().get("uuid"));
    }

    @Test
    public void testTraceIdPreservation() {
        Context context = new Context();
        context.put("fields", "trace_id");
        builder = new FieldInjectionInterceptor.Builder();
        builder.configure(context);
        interceptor = (FieldInjectionInterceptor) builder.build();

        Event event = new SimpleEvent();
        event.setBody("Test log".getBytes());
        Map<String, String> headers = new HashMap<>();
        headers.put("trace_id", "existing-trace-id-123");
        event.setHeaders(headers);

        Event result = interceptor.intercept(event);

        assertEquals("existing-trace-id-123", result.getHeaders().get("trace_id"));
    }
}
