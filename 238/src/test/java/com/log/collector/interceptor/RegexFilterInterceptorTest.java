package com.log.collector.interceptor;

import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.event.SimpleEvent;
import org.junit.Test;

import java.nio.charset.StandardCharsets;

import static org.junit.Assert.*;

public class RegexFilterInterceptorTest {

    @Test
    public void testIncludeFilter() {
        Context context = new Context();
        context.put("includeRegex", ".*(ERROR|WARN).*");

        RegexFilterInterceptor.Builder builder = new RegexFilterInterceptor.Builder();
        builder.configure(context);
        RegexFilterInterceptor interceptor = (RegexFilterInterceptor) builder.build();

        Event errorEvent = new SimpleEvent();
        errorEvent.setBody("[ERROR] Something went wrong".getBytes(StandardCharsets.UTF_8));
        assertNotNull("ERROR日志应该被保留", interceptor.intercept(errorEvent));

        Event warnEvent = new SimpleEvent();
        warnEvent.setBody("[WARN] This is a warning".getBytes(StandardCharsets.UTF_8));
        assertNotNull("WARN日志应该被保留", interceptor.intercept(warnEvent));

        Event infoEvent = new SimpleEvent();
        infoEvent.setBody("[INFO] Normal log message".getBytes(StandardCharsets.UTF_8));
        assertNull("INFO日志应该被过滤", interceptor.intercept(infoEvent));
    }

    @Test
    public void testExcludeFilter() {
        Context context = new Context();
        context.put("excludeRegex", ".*healthcheck.*");

        RegexFilterInterceptor.Builder builder = new RegexFilterInterceptor.Builder();
        builder.configure(context);
        RegexFilterInterceptor interceptor = (RegexFilterInterceptor) builder.build();

        Event normalEvent = new SimpleEvent();
        normalEvent.setBody("[INFO] Normal log".getBytes(StandardCharsets.UTF_8));
        assertNotNull("正常日志应该被保留", interceptor.intercept(normalEvent));

        Event healthEvent = new SimpleEvent();
        healthEvent.setBody("[INFO] /api/healthcheck called".getBytes(StandardCharsets.UTF_8));
        assertNull("健康检查日志应该被过滤", interceptor.intercept(healthEvent));
    }

    @Test
    public void testCombinedFilter() {
        Context context = new Context();
        context.put("includeRegex", ".*(ERROR|WARN).*");
        context.put("excludeRegex", ".*ignore.*");

        RegexFilterInterceptor.Builder builder = new RegexFilterInterceptor.Builder();
        builder.configure(context);
        RegexFilterInterceptor interceptor = (RegexFilterInterceptor) builder.build();

        Event errorEvent = new SimpleEvent();
        errorEvent.setBody("[ERROR] Critical error".getBytes(StandardCharsets.UTF_8));
        assertNotNull("ERROR日志应该被保留", interceptor.intercept(errorEvent));

        Event ignoreEvent = new SimpleEvent();
        ignoreEvent.setBody("[ERROR] ignore this error".getBytes(StandardCharsets.UTF_8));
        assertNull("包含ignore的ERROR日志应该被过滤", interceptor.intercept(ignoreEvent));
    }

    @Test
    public void testBatchIntercept() {
        Context context = new Context();
        context.put("includeRegex", ".*ERROR.*");

        RegexFilterInterceptor.Builder builder = new RegexFilterInterceptor.Builder();
        builder.configure(context);
        RegexFilterInterceptor interceptor = (RegexFilterInterceptor) builder.build();

        java.util.List<Event> events = new java.util.ArrayList<>();
        for (int i = 0; i < 10; i++) {
            Event e = new SimpleEvent();
            String level = i % 2 == 0 ? "ERROR" : "INFO";
            e.setBody(("[" + level + "] Log message " + i).getBytes(StandardCharsets.UTF_8));
            events.add(e);
        }

        java.util.List<Event> result = interceptor.intercept(events);
        assertEquals("应该只保留ERROR日志", 5, result.size());
    }
}
