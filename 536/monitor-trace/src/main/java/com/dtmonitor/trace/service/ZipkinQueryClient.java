package com.dtmonitor.trace.service;

import com.dtmonitor.trace.model.TraceSpan;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Slf4j
@Component
public class ZipkinQueryClient {

    @Value("${zipkin.base-url:http://localhost:9411}")
    private String zipkinBaseUrl;

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<TraceSpan> fetchSpans(String traceId) {
        try {
            String url = zipkinBaseUrl + "/api/v2/trace/" + traceId;
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);

            if (response.getBody() == null) {
                return Collections.emptyList();
            }

            JsonNode root = objectMapper.readTree(response.getBody());
            List<TraceSpan> spans = new ArrayList<>();

            if (root.isArray()) {
                for (JsonNode spanNode : root) {
                    TraceSpan span = parseSpan(spanNode);
                    spans.add(span);
                }
            }

            return spans;
        } catch (Exception e) {
            log.error("Failed to fetch spans from Zipkin for traceId: {}", traceId, e);
            return Collections.emptyList();
        }
    }

    private TraceSpan parseSpan(JsonNode node) {
        TraceSpan.TraceSpanBuilder builder = TraceSpan.builder()
                .traceId(getText(node, "traceId"))
                .spanId(getText(node, "id"))
                .parentSpanId(getText(node, "parentId"))
                .name(getText(node, "name"))
                .kind(getText(node, "kind"))
                .startMicros(node.path("timestamp").asLong(0))
                .endMicros(node.path("timestamp").asLong(0) + node.path("duration").asLong(0))
                .durationMicros(node.path("duration").asLong(0));

        String localServiceName = node.path("localEndpoint").path("serviceName").asText("");
        builder.serviceName(localServiceName);

        List<TraceSpan.KeyValue> tags = new ArrayList<>();
        JsonNode tagsNode = node.path("tags");
        if (tagsNode.isObject()) {
            tagsNode.fields().forEachRemaining(entry ->
                    tags.add(TraceSpan.KeyValue.builder()
                            .key(entry.getKey())
                            .value(entry.getValue().asText())
                            .build()));
        }
        builder.tags(tags);

        List<TraceSpan.Annotation> annotations = new ArrayList<>();
        JsonNode annNode = node.path("annotations");
        if (annNode.isArray()) {
            for (JsonNode a : annNode) {
                annotations.add(TraceSpan.Annotation.builder()
                        .timestamp(a.path("timestamp").asLong(0))
                        .value(a.path("value").asText())
                        .build());
            }
        }
        builder.annotations(annotations);

        return builder.build();
    }

    private String getText(JsonNode node, String field) {
        JsonNode f = node.path(field);
        return f.isMissingNode() ? null : f.asText();
    }
}
