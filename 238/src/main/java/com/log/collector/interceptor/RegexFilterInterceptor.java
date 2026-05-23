package com.log.collector.interceptor;

import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.interceptor.Interceptor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

public class RegexFilterInterceptor implements Interceptor {

    private static final Logger logger = LoggerFactory.getLogger(RegexFilterInterceptor.class);

    private final Pattern includePattern;
    private final Pattern excludePattern;
    private final boolean filterOnMatch;

    private RegexFilterInterceptor(Builder builder) {
        this.includePattern = builder.includePattern;
        this.excludePattern = builder.excludePattern;
        this.filterOnMatch = builder.filterOnMatch;
    }

    @Override
    public void initialize() {
    }

    @Override
    public Event intercept(Event event) {
        String body = new String(event.getBody(), StandardCharsets.UTF_8);

        boolean shouldInclude = true;

        if (includePattern != null) {
            shouldInclude = includePattern.matcher(body).matches();
        }

        if (shouldInclude && excludePattern != null) {
            shouldInclude = !excludePattern.matcher(body).matches();
        }

        if (filterOnMatch) {
            return shouldInclude ? event : null;
        } else {
            return shouldInclude ? null : event;
        }
    }

    @Override
    public List<Event> intercept(List<Event> events) {
        List<Event> intercepted = new ArrayList<>();
        for (Event event : events) {
            Event interceptedEvent = intercept(event);
            if (interceptedEvent != null) {
                intercepted.add(interceptedEvent);
            }
        }
        return intercepted;
    }

    @Override
    public void close() {
    }

    public static class Builder implements Interceptor.Builder {

        private Pattern includePattern;
        private Pattern excludePattern;
        private boolean filterOnMatch = true;

        @Override
        public Interceptor build() {
            return new RegexFilterInterceptor(this);
        }

        @Override
        public void configure(Context context) {
            String includeRegex = context.getString("includeRegex", null);
            String excludeRegex = context.getString("excludeRegex", null);
            filterOnMatch = context.getBoolean("filterOnMatch", true);

            if (includeRegex != null && !includeRegex.isEmpty()) {
                includePattern = Pattern.compile(includeRegex, Pattern.DOTALL);
                logger.info("Include regex pattern configured: {}", includeRegex);
            }

            if (excludeRegex != null && !excludeRegex.isEmpty()) {
                excludePattern = Pattern.compile(excludeRegex, Pattern.DOTALL);
                logger.info("Exclude regex pattern configured: {}", excludeRegex);
            }
        }
    }
}
