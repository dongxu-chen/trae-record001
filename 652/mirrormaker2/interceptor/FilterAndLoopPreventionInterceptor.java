package com.kafkamirror.interceptor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.kafka.clients.consumer.ConsumerInterceptor;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.Configurable;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Pattern;

public class FilterAndLoopPreventionInterceptor implements ConsumerInterceptor<byte[], byte[]>, Configurable {

    private Pattern keyPattern;
    private Pattern valuePattern;
    private Pattern topicPattern;
    private boolean loopPreventionEnabled;
    private String hopHeaderKey;
    private int maxHops;
    private ObjectMapper objectMapper;
    private List<JsonPathFilter> jsonPathFilters;

    private static class JsonPathFilter {
        String[] pathSegments;
        String operator;
        String value;
    }

    @Override
    public void configure(Map<String, ?> configs) {
        String keyRegex = (String) configs.get("filter.key.regex");
        String valueRegex = (String) configs.get("filter.value.regex");
        String topicRegex = (String) configs.get("filter.topic.regex");

        if (keyRegex != null && !keyRegex.isEmpty()) {
            keyPattern = Pattern.compile(keyRegex);
        }
        if (valueRegex != null && !valueRegex.isEmpty()) {
            valuePattern = Pattern.compile(valueRegex);
        }
        if (topicRegex != null && !topicRegex.isEmpty()) {
            topicPattern = Pattern.compile(topicRegex);
        }

        loopPreventionEnabled = Boolean.parseBoolean(
            (String) configs.getOrDefault("loop.prevention.enabled", "true")
        );
        hopHeaderKey = (String) configs.getOrDefault("loop.prevention.header_key", "x-mirror-hop");
        maxHops = Integer.parseInt((String) configs.getOrDefault("loop.prevention.max_hops", "15"));

        objectMapper = new ObjectMapper();
        jsonPathFilters = new ArrayList<>();
    }

    @Override
    public ConsumerRecords<byte[], byte[]> onConsume(ConsumerRecords<byte[], byte[]> records) {
        Map<org.apache.kafka.common.TopicPartition, List<ConsumerRecord<byte[], byte[]>>> filteredRecords = new HashMap<>();

        for (ConsumerRecord<byte[], byte[]> record : records) {
            if (shouldSkipRecord(record)) {
                continue;
            }

            org.apache.kafka.common.TopicPartition tp = new org.apache.kafka.common.TopicPartition(
                record.topic(), record.partition()
            );
            filteredRecords.computeIfAbsent(tp, k -> new ArrayList<>()).add(record);
        }

        return new ConsumerRecords<>(filteredRecords);
    }

    private boolean shouldSkipRecord(ConsumerRecord<byte[], byte[]> record) {
        if (loopPreventionEnabled && shouldDropByHopCount(record)) {
            return true;
        }

        if (keyPattern != null && record.key() != null) {
            if (!keyPattern.matcher(new String(record.key())).matches()) {
                return true;
            }
        }

        if (valuePattern != null && record.value() != null) {
            if (!valuePattern.matcher(new String(record.value())).matches()) {
                return true;
            }
        }

        if (topicPattern != null) {
            if (!topicPattern.matcher(record.topic()).matches()) {
                return true;
            }
        }

        if (!jsonPathFilters.isEmpty() && record.value() != null) {
            if (!matchJsonPaths(record.value())) {
                return true;
            }
        }

        return false;
    }

    private boolean shouldDropByHopCount(ConsumerRecord<byte[], byte[]> record) {
        for (Header header : record.headers()) {
            if (hopHeaderKey.equals(header.key())) {
                try {
                    String headerValue = new String(header.value(), StandardCharsets.UTF_8);
                    JsonNode hopNode = objectMapper.readTree(headerValue);
                    int hopCount = hopNode.get("hop_count").asInt();
                    if (hopCount <= 0) {
                        return true;
                    }
                } catch (Exception e) {
                    return true;
                }
            }
        }
        return false;
    }

    private boolean matchJsonPaths(byte[] data) {
        try {
            JsonNode root = objectMapper.readTree(data);
            for (JsonPathFilter filter : jsonPathFilters) {
                JsonNode node = resolvePath(root, filter.pathSegments);
                if (node == null || node.isMissingNode()) {
                    return false;
                }
                String actualValue = node.asText();
                if (!matchOperator(actualValue, filter.operator, filter.value)) {
                    return false;
                }
            }
            return true;
        } catch (IOException e) {
            return false;
        }
    }

    private JsonNode resolvePath(JsonNode root, String[] segments) {
        JsonNode current = root;
        for (String segment : segments) {
            if (current.isArray()) {
                int idx;
                try {
                    idx = Integer.parseInt(segment);
                } catch (NumberFormatException e) {
                    return null;
                }
                if (idx < 0 || idx >= current.size()) {
                    return null;
                }
                current = current.get(idx);
            } else if (current.isObject()) {
                current = current.get(segment);
            } else {
                return null;
            }
            if (current == null || current.isMissingNode()) {
                return null;
            }
        }
        return current;
    }

    private boolean matchOperator(String actual, String operator, String expected) {
        switch (operator) {
            case "eq":
            case "==":
            case "=":
                return actual.equals(expected);
            case "neq":
            case "!=":
                return !actual.equals(expected);
            case "contains":
                return actual.contains(expected);
            case "prefix":
                return actual.startsWith(expected);
            case "suffix":
                return actual.endsWith(expected);
            case "gt":
                return Double.parseDouble(actual) > Double.parseDouble(expected);
            case "gte":
                return Double.parseDouble(actual) >= Double.parseDouble(expected);
            case "lt":
                return Double.parseDouble(actual) < Double.parseDouble(expected);
            case "lte":
                return Double.parseDouble(actual) <= Double.parseDouble(expected);
            case "regex":
                return Pattern.compile(expected).matcher(actual).matches();
            case "exists":
                return actual != null && !actual.isEmpty();
            default:
                return actual.equals(expected);
        }
    }

    @Override
    public void onCommit(Map<org.apache.kafka.common.TopicPartition, org.apache.kafka.clients.consumer.OffsetAndMetadata> offsets) {
    }

    @Override
    public void close() {
    }
}
