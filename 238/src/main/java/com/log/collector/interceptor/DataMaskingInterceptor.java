package com.log.collector.interceptor;

import com.log.collector.util.MaskingRuleManager;
import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.interceptor.Interceptor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DataMaskingInterceptor implements Interceptor {

    private static final Logger logger = LoggerFactory.getLogger(DataMaskingInterceptor.class);

    private final Set<String> maskFields;
    private final boolean maskBody;
    private final MaskingRuleManager ruleManager;

    private DataMaskingInterceptor(Builder builder) {
        this.maskFields = builder.maskFields;
        this.maskBody = builder.maskBody;
        this.ruleManager = MaskingRuleManager.getInstance();
    }

    @Override
    public void initialize() {
    }

    @Override
    public Event intercept(Event event) {
        if (!maskFields.isEmpty()) {
            maskHeaders(event);
        }

        if (maskBody) {
            maskBody(event);
        }

        return event;
    }

    private void maskHeaders(Event event) {
        for (String field : maskFields) {
            String value = event.getHeaders().get(field);
            if (value != null && !value.isEmpty()) {
                String maskedValue = ruleManager.applyMasking(value);
                event.getHeaders().put(field, maskedValue);
            }
        }
    }

    private void maskBody(Event event) {
        String body = new String(event.getBody(), StandardCharsets.UTF_8);
        String maskedBody = ruleManager.applyMasking(body);
        event.setBody(maskedBody.getBytes(StandardCharsets.UTF_8));
    }

    @Override
    public List<Event> intercept(List<Event> events) {
        List<Event> intercepted = new ArrayList<>();
        for (Event event : events) {
            intercepted.add(intercept(event));
        }
        return intercepted;
    }

    @Override
    public void close() {
    }

    public static class Builder implements Interceptor.Builder {

        private Set<String> maskFields = new HashSet<>();
        private boolean maskBody = true;
        private String configFilePath;
        private boolean enableHotReload = true;

        @Override
        public Interceptor build() {
            MaskingRuleManager ruleManager = MaskingRuleManager.getInstance();
            try {
                ruleManager.init(configFilePath, enableHotReload);
            } catch (Exception e) {
                logger.warn("Failed to initialize MaskingRuleManager, using default rules", e);
            }
            return new DataMaskingInterceptor(this);
        }

        @Override
        public void configure(Context context) {
            maskBody = context.getBoolean("maskBody", true);
            configFilePath = context.getString("configFilePath", "conf/masking-rules.json");
            enableHotReload = context.getBoolean("enableHotReload", true);

            String fieldsStr = context.getString("maskFields", null);
            if (fieldsStr != null && !fieldsStr.isEmpty()) {
                String[] fields = fieldsStr.split(",");
                for (String field : fields) {
                    maskFields.add(field.trim());
                }
                logger.info("Fields to mask: {}", maskFields);
            }

            logger.info("DataMaskingInterceptor configured - body: {}, config: {}, hotReload: {}",
                    maskBody, configFilePath, enableHotReload);
        }
    }
}
