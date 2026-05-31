package com.log.mask.flume;

import com.log.mask.config.MaskConfig;
import com.log.mask.parser.LogParser;
import com.log.mask.parser.LogParserFactory;
import com.log.mask.rule.RuleEngine;
import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.interceptor.Interceptor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class MaskingInterceptor implements Interceptor {
    private static final Logger logger = LoggerFactory.getLogger(MaskingInterceptor.class);
    
    private final RuleEngine ruleEngine;
    private final LogParser logParser;

    private MaskingInterceptor(Builder builder) {
        this.ruleEngine = builder.ruleEngine;
        this.logParser = builder.logParser;
    }

    @Override
    public void initialize() {
        logger.info("MaskingInterceptor initialized");
    }

    @Override
    public Event intercept(Event event) {
        if (event == null) {
            return null;
        }
        try {
            String originalLog = new String(event.getBody());
            String maskedLog = logParser.parseAndMask(originalLog, ruleEngine.getMaskEngine());
            event.setBody(maskedLog.getBytes());
            return event;
        } catch (Exception e) {
            logger.error("Error masking event", e);
            return event;
        }
    }

    @Override
    public List<Event> intercept(List<Event> events) {
        List<Event> intercepted = new ArrayList<>(events.size());
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
        logger.info("MaskingInterceptor closed");
    }

    public static class Builder implements Interceptor.Builder {
        private RuleEngine ruleEngine;
        private LogParser logParser;
        private String logFormat;
        private String configFile;

        @Override
        public Interceptor build() {
            return new MaskingInterceptor(this);
        }

        @Override
        public void configure(Context context) {
            logFormat = context.getString("log.format", "text");
            configFile = context.getString("config.file", "mask-config.properties");
            
            ruleEngine = new RuleEngine();
            logParser = LogParserFactory.getParser(logFormat);
            
            try {
                MaskConfig config = new MaskConfig();
                config.loadFromFile(configFile);
                
                if (!config.isEnableDefaultRules()) {
                    ruleEngine.clearAllRules();
                }
                ruleEngine.addRules(config.getCustomRules());
                
                if (config.getLogFormat() != null) {
                    logParser = LogParserFactory.getParser(config.getLogFormat());
                }
                
                logger.info("MaskingInterceptor configured with format: {}", logFormat);
            } catch (IOException e) {
                logger.warn("Could not load config file, using default rules: {}", e.getMessage());
            }
        }
    }
}
