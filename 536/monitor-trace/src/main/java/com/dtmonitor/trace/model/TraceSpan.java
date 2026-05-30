package com.dtmonitor.trace.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TraceSpan {

    private String traceId;
    private String spanId;
    private String parentSpanId;
    private String name;
    private String serviceName;
    private long startMicros;
    private long endMicros;
    private long durationMicros;
    private String kind;
    private List<KeyValue> tags;
    private List<Annotation> annotations;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class KeyValue {
        private String key;
        private String value;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Annotation {
        private long timestamp;
        private String value;
    }

    public void addTag(String key, String value) {
        if (tags == null) tags = new ArrayList<>();
        tags.add(KeyValue.builder().key(key).value(value).build());
    }
}
