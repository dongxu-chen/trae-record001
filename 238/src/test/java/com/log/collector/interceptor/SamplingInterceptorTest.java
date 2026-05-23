package com.log.collector.interceptor;

import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.event.SimpleEvent;
import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

import static org.junit.Assert.*;

public class SamplingInterceptorTest {

    private SamplingInterceptor.Builder builder;
    private SamplingInterceptor interceptor;

    @Before
    public void setUp() {
        builder = new SamplingInterceptor.Builder();
        Context context = new Context();
        context.put("sampleRate.debug", "0.01");
        context.put("sampleRate.info", "0.1");
        context.put("sampleRate.warn", "0.5");
        context.put("sampleRate.error", "1.0");
        context.put("forceErrorFull", "true");
        builder.configure(context);
        interceptor = (SamplingInterceptor) builder.build();
        interceptor.initialize();
    }

    @Test
    public void testErrorFullSampling() {
        for (int i = 0; i < 100; i++) {
            Event event = new SimpleEvent();
            event.setBody("2024-01-01 10:00:00 ERROR test error message".getBytes());
            event.setHeaders(new HashMap<>());
            Event result = interceptor.intercept(event);
            assertNotNull("ERROR level should always be sampled", result);
        }
        assertEquals(100, interceptor.getSampledEvents());
    }

    @Test
    public void testDebugSampling() {
        builder = new SamplingInterceptor.Builder();
        Context context = new Context();
        context.put("sampleRate.debug", "0.0");
        builder.configure(context);
        interceptor = (SamplingInterceptor) builder.build();

        for (int i = 0; i < 100; i++) {
            Event event = new SimpleEvent();
            event.setBody("2024-01-01 10:00:00 DEBUG test debug message".getBytes());
            event.setHeaders(new HashMap<>());
            Event result = interceptor.intercept(event);
            assertNull("DEBUG with 0% rate should not be sampled", result);
        }
    }

    @Test
    public void testInfoSamplingStatistical() {
        builder = new SamplingInterceptor.Builder();
        Context context = new Context();
        context.put("sampleRate.info", "0.5");
        context.put("forceErrorFull", "false");
        builder.configure(context);
        interceptor = (SamplingInterceptor) builder.build();

        int total = 10000;
        for (int i = 0; i < total; i++) {
            Event event = new SimpleEvent();
            event.setBody("2024-01-01 10:00:00 INFO test info message".getBytes());
            event.setHeaders(new HashMap<>());
            interceptor.intercept(event);
        }

        double actualRate = interceptor.getActualSampleRate();
        assertTrue("Sampling rate should be around 50%", actualRate > 0.4 && actualRate < 0.6);
        assertEquals(total, interceptor.getTotalEvents());
    }

    @Test
    public void testBatchSampling() {
        List<Event> events = new ArrayList<>();
        for (int i = 0; i < 100; i++) {
            Event event = new SimpleEvent();
            event.setBody(("2024-01-01 10:00:00 ERROR test error " + i).getBytes());
            event.setHeaders(new HashMap<>());
            events.add(event);
        }

        List<Event> result = interceptor.intercept(events);
        assertEquals(100, result.size());
    }

    @Test
    public void testLogLevelExtraction() {
        Event event = new SimpleEvent();
        event.setBody("[2024-01-01 10:00:00] WARN - warning message".getBytes());
        event.setHeaders(new HashMap<>());
        Event result = interceptor.intercept(event);
        assertNotNull(result);
        assertEquals("WARN", result.getHeaders().get("log_level"));
    }

    @Test
    public void testHeaderLevelField() {
        builder = new SamplingInterceptor.Builder();
        Context context = new Context();
        context.put("useHeaderField", "true");
        context.put("levelField", "severity");
        builder.configure(context);
        interceptor = (SamplingInterceptor) builder.build();

        Event event = new SimpleEvent();
        event.setBody("some message".getBytes());
        HashMap<String, String> headers = new HashMap<>();
        headers.put("severity", "ERROR");
        event.setHeaders(headers);

        Event result = interceptor.intercept(event);
        assertNotNull(result);
        assertEquals("ERROR", result.getHeaders().get("log_level"));
        assertEquals("1.0", result.getHeaders().get("sample_rate"));
    }
}
