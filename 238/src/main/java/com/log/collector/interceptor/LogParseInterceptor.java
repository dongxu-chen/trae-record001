package com.log.collector.interceptor;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.interceptor.Interceptor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class LogParseInterceptor implements Interceptor {

    private static final Logger logger = LoggerFactory.getLogger(LogParseInterceptor.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    private final String format;
    private final Pattern logstashPattern;
    private final boolean flattenNested;
    private final String timestampField;

    private LogParseInterceptor(Builder builder) {
        this.format = builder.format;
        this.logstashPattern = builder.logstashPattern;
        this.flattenNested = builder.flattenNested;
        this.timestampField = builder.timestampField;
    }

    @Override
    public void initialize() {
    }

    @Override
    public Event intercept(Event event) {
        String body = new String(event.getBody(), StandardCharsets.UTF_8);
        Map<String, String> headers = event.getHeaders();

        try {
            Map<String, Object> parsedFields;

            if ("logstash".equalsIgnoreCase(format)) {
                parsedFields = parseLogstashFormat(body);
            } else {
                parsedFields = parseJsonFormat(body);
            }

            if (flattenNested) {
                parsedFields = flattenMap(parsedFields, "");
            }

            for (Map.Entry<String, Object> entry : parsedFields.entrySet()) {
                String key = entry.getKey();
                String value = entry.getValue() != null ? String.valueOf(entry.getValue()) : "";
                if (!headers.containsKey(key)) {
                    headers.put(key, value);
                }
            }

            if (timestampField != null && parsedFields.containsKey(timestampField)) {
                headers.put("parsed_timestamp", String.valueOf(parsedFields.get(timestampField)));
            }

            headers.put("parse_status", "success");

        } catch (Exception e) {
            headers.put("parse_status", "failed");
            headers.put("parse_error", e.getMessage());
            logger.debug("Failed to parse log: {}", e.getMessage());
        }

        return event;
    }

    private Map<String, Object> parseJsonFormat(String body) throws Exception {
        JsonNode rootNode = objectMapper.readTree(body);
        return objectMapper.convertValue(rootNode, new TypeReference<Map<String, Object>>() {});
    }

    private Map<String, Object> parseLogstashFormat(String body) {
        Map<String, Object> fields = new HashMap<>();

        Matcher matcher = logstashPattern.matcher(body);
        if (matcher.matches()) {
            for (int i = 1; i <= matcher.groupCount(); i++) {
                String groupName = getGroupName(logstashPattern, i);
                if (groupName != null) {
                    fields.put(groupName, matcher.group(i));
                }
            }
        }

        return fields;
    }

    private String getGroupName(Pattern pattern, int groupIndex) {
        try {
            java.lang.reflect.Field f = Pattern.class.getDeclaredField("namedGroups");
            f.setAccessible(true);
            @SuppressWarnings("unchecked")
            Map<String, Integer> namedGroups = (Map<String, Integer>) f.get(pattern);
            for (Map.Entry<String, Integer> entry : namedGroups.entrySet()) {
                if (entry.getValue() == groupIndex) {
                    return entry.getKey();
                }
            }
        } catch (Exception e) {
            return "group" + groupIndex;
        }
        return "group" + groupIndex;
    }

    private Map<String, Object> flattenMap(Map<String, Object> map, String prefix) {
        Map<String, Object> result = new HashMap<>();

        for (Map.Entry<String, Object> entry : map.entrySet()) {
            String key = prefix.isEmpty() ? entry.getKey() : prefix + "_" + entry.getKey();
            Object value = entry.getValue();

            if (value instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> nestedMap = (Map<String, Object>) value;
                result.putAll(flattenMap(nestedMap, key));
            } else if (value instanceof List) {
                @SuppressWarnings("unchecked")
                List<Object> list = (List<Object>) value;
                result.put(key, listToString(list));
            } else {
                result.put(key, value);
            }
        }

        return result;
    }

    private String listToString(List<Object> list) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(list.get(i));
        }
        return sb.toString();
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

        private String format = "json";
        private Pattern logstashPattern;
        private boolean flattenNested = true;
        private String timestampField = "@timestamp";

        @Override
        public Interceptor build() {
            return new LogParseInterceptor(this);
        }

        @Override
        public void configure(Context context) {
            format = context.getString("format", "json");
            flattenNested = context.getBoolean("flattenNested", true);
            timestampField = context.getString("timestampField", "@timestamp");

            String logstashRegex = context.getString("logstashPattern", null);
            if (logstashRegex != null && !logstashRegex.isEmpty()) {
                logstashPattern = Pattern.compile(logstashRegex);
                logger.info("Logstash pattern configured: {}", logstashRegex);
            }

            logger.info("LogParseInterceptor configured - format: {}, flattenNested: {}", 
                    format, flattenNested);
        }
    }
}
