package com.log.collector.interceptor;

import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.interceptor.Interceptor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SamplingInterceptor implements Interceptor {

    private static final Logger logger = LoggerFactory.getLogger(SamplingInterceptor.class);

    private final Map<String, Double> levelSampleRates;
    private final double defaultSampleRate;
    private final Pattern levelPattern;
    private final String levelField;
    private final boolean useHeaderField;
    private final Random random;
    private final boolean forceErrorFull;

    private final AtomicLong totalEvents = new AtomicLong(0);
    private final AtomicLong sampledEvents = new AtomicLong(0);

    private SamplingInterceptor(Builder builder) {
        this.levelSampleRates = builder.levelSampleRates;
        this.defaultSampleRate = builder.defaultSampleRate;
        this.levelPattern = builder.levelPattern;
        this.levelField = builder.levelField;
        this.useHeaderField = builder.useHeaderField;
        this.forceErrorFull = builder.forceErrorFull;
        this.random = new Random();
    }

    @Override
    public void initialize() {
    }

    @Override
    public Event intercept(Event event) {
        totalEvents.incrementAndGet();

        String logLevel = extractLogLevel(event);
        double sampleRate = getSampleRate(logLevel);

        if (forceErrorFull && isErrorLevel(logLevel)) {
            sampledEvents.incrementAndGet();
            event.getHeaders().put("sampled", "true");
            event.getHeaders().put("sample_rate", "1.0");
            event.getHeaders().put("log_level", logLevel);
            return event;
        }

        if (sampleRate >= 1.0) {
            sampledEvents.incrementAndGet();
            event.getHeaders().put("sampled", "true");
            event.getHeaders().put("sample_rate", String.valueOf(sampleRate));
            event.getHeaders().put("log_level", logLevel);
            return event;
        }

        if (sampleRate <= 0.0) {
            return null;
        }

        if (random.nextDouble() < sampleRate) {
            sampledEvents.incrementAndGet();
            event.getHeaders().put("sampled", "true");
            event.getHeaders().put("sample_rate", String.valueOf(sampleRate));
            event.getHeaders().put("log_level", logLevel);
            return event;
        }

        return null;
    }

    private String extractLogLevel(Event event) {
        if (useHeaderField && levelField != null) {
            String level = event.getHeaders().get(levelField);
            if (level != null && !level.isEmpty()) {
                return level.toUpperCase();
            }
        }

        String body = new String(event.getBody(), StandardCharsets.UTF_8);
        Matcher matcher = levelPattern.matcher(body);
        if (matcher.find()) {
            return matcher.group(1).toUpperCase();
        }

        return "UNKNOWN";
    }

    private double getSampleRate(String logLevel) {
        Double rate = levelSampleRates.get(logLevel);
        if (rate != null) {
            return rate;
        }
        return defaultSampleRate;
    }

    private boolean isErrorLevel(String logLevel) {
        return "ERROR".equals(logLevel) || "FATAL".equals(logLevel) || "CRITICAL".equals(logLevel);
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

    public long getTotalEvents() {
        return totalEvents.get();
    }

    public long getSampledEvents() {
        return sampledEvents.get();
    }

    public double getActualSampleRate() {
        long total = totalEvents.get();
        if (total == 0) {
            return 0.0;
        }
        return (double) sampledEvents.get() / total;
    }

    @Override
    public void close() {
        logger.info("Sampling stats - total: {}, sampled: {}, rate: {:.4f}",
                totalEvents.get(), sampledEvents.get(), getActualSampleRate());
    }

    public static class Builder implements Interceptor.Builder {

        private Map<String, Double> levelSampleRates = new HashMap<>();
        private double defaultSampleRate = 1.0;
        private Pattern levelPattern;
        private String levelField;
        private boolean useHeaderField = false;
        private boolean forceErrorFull = true;

        @Override
        public Interceptor build() {
            return new SamplingInterceptor(this);
        }

        @Override
        public void configure(Context context) {
            defaultSampleRate = context.getDouble("defaultSampleRate", 1.0);
            useHeaderField = context.getBoolean("useHeaderField", false);
            levelField = context.getString("levelField", "level");
            forceErrorFull = context.getBoolean("forceErrorFull", true);

            String levelPatternStr = context.getString("levelPattern",
                    "(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE|CRITICAL)");
            levelPattern = Pattern.compile(levelPatternStr);

            for (String level : new String[]{"DEBUG", "TRACE", "INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"}) {
                String rateKey = "sampleRate." + level.toLowerCase();
                if (context.containsKey(rateKey)) {
                    double rate = context.getDouble(rateKey, 1.0);
                    levelSampleRates.put(level, rate);
                    logger.info("Sampling rate for {}: {}", level, rate);
                }
            }

            if (!levelSampleRates.containsKey("DEBUG")) {
                levelSampleRates.put("DEBUG", 0.01);
            }
            if (!levelSampleRates.containsKey("TRACE")) {
                levelSampleRates.put("TRACE", 0.01);
            }
            if (!levelSampleRates.containsKey("INFO")) {
                levelSampleRates.put("INFO", 0.1);
            }
            if (!levelSampleRates.containsKey("WARN")) {
                levelSampleRates.put("WARN", 0.5);
                levelSampleRates.put("WARNING", 0.5);
            }
            if (!levelSampleRates.containsKey("ERROR")) {
                levelSampleRates.put("ERROR", 1.0);
                levelSampleRates.put("FATAL", 1.0);
                levelSampleRates.put("CRITICAL", 1.0);
            }

            logger.info("SamplingInterceptor configured - defaultRate: {}, forceErrorFull: {}",
                    defaultSampleRate, forceErrorFull);
        }
    }
}
