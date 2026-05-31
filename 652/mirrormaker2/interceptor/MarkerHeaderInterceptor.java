package com.kafkamirror.interceptor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.kafka.clients.producer.ProducerInterceptor;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.header.internals.RecordHeader;
import org.apache.kafka.common.Configurable;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;

public class MarkerHeaderInterceptor implements ProducerInterceptor<byte[], byte[]>, Configurable {

    private String hopHeaderKey;
    private int maxHops;
    private ObjectMapper objectMapper;

    @Override
    public void configure(Map<String, ?> configs) {
        hopHeaderKey = (String) configs.getOrDefault("loop.prevention.header_key", "x-mirror-hop");
        maxHops = Integer.parseInt((String) configs.getOrDefault("loop.prevention.max_hops", "15"));
        objectMapper = new ObjectMapper();
    }

    @Override
    public ProducerRecord<byte[], byte[]> onSend(ProducerRecord<byte[], byte[]> record) {
        String traceId = null;
        int hopCount = maxHops;

        for (Header header : record.headers()) {
            if (hopHeaderKey.equals(header.key())) {
                try {
                    String headerValue = new String(header.value(), StandardCharsets.UTF_8);
                    JsonNode hopNode = objectMapper.readTree(headerValue);
                    traceId = hopNode.get("trace_id").asText();
                    hopCount = hopNode.get("hop_count").asInt() - 1;
                } catch (Exception e) {
                    traceId = UUID.randomUUID().toString();
                    hopCount = maxHops - 1;
                }
                record.headers().remove(hopHeaderKey);
                break;
            }
        }

        if (traceId == null) {
            traceId = UUID.randomUUID().toString();
            hopCount = maxHops - 1;
        }

        ObjectNode hopObject = objectMapper.createObjectNode();
        hopObject.put("trace_id", traceId);
        hopObject.put("hop_count", hopCount);

        try {
            byte[] hopBytes = objectMapper.writeValueAsBytes(hopObject);
            record.headers().add(new RecordHeader(hopHeaderKey, hopBytes));
        } catch (Exception e) {
            ObjectNode fallback = objectMapper.createObjectNode();
            fallback.put("trace_id", UUID.randomUUID().toString());
            fallback.put("hop_count", maxHops - 1);
            try {
                record.headers().add(new RecordHeader(hopHeaderKey, objectMapper.writeValueAsBytes(fallback)));
            } catch (Exception ignored) {
            }
        }

        return record;
    }

    @Override
    public void onAcknowledgement(RecordMetadata metadata, Exception exception) {
    }

    @Override
    public void close() {
    }
}
