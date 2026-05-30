package com.loganalytics.functions;

import com.loganalytics.model.NginxLogEvent;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.util.Collector;
import org.junit.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.junit.Assert.*;

public class DimensionExtractorTest {

    @Test
    public void testPredefinedDimensionCombinations() {
        List<Tuple2<String, NginxLogEvent>> output = new ArrayList<>();
        Collector<Tuple2<String, NginxLogEvent>> collector = new ListCollector<>(output);

        DimensionExtractor extractor = new DimensionExtractor.Builder()
                .enableAll()
                .enableApi()
                .enableStatus()
                .enableApiStatus()
                .enableApiMethod()
                .enableMethod()
                .enableHost()
                .build();

        NginxLogEvent event = createTestEvent();
        extractor.flatMap(event, collector);

        Set<String> keys = new HashSet<>();
        for (Tuple2<String, NginxLogEvent> tuple : output) {
            keys.add(tuple.f0);
        }

        assertTrue(keys.contains("all:total"));
        assertTrue(keys.contains("api:/api/v1/users"));
        assertTrue(keys.contains("status:200"));
        assertTrue(keys.contains("api_status:/api/v1/users|200"));
        assertTrue(keys.contains("api_method:/api/v1/users|GET"));
        assertTrue(keys.contains("method:GET"));
        assertTrue(keys.contains("host:api.example.com"));
        assertFalse(keys.contains("ip:192.168.1.100"));
    }

    @Test
    public void testIpDimensionDisabledByDefault() {
        List<Tuple2<String, NginxLogEvent>> output = new ArrayList<>();
        Collector<Tuple2<String, NginxLogEvent>> collector = new ListCollector<>(output);

        DimensionExtractor extractor = new DimensionExtractor();

        NginxLogEvent event = createTestEvent();
        extractor.flatMap(event, collector);

        Set<String> keys = new HashSet<>();
        for (Tuple2<String, NginxLogEvent> tuple : output) {
            keys.add(tuple.f0);
        }

        assertFalse(keys.contains("ip:192.168.1.100"));
    }

    @Test
    public void testEnableIpDimension() {
        List<Tuple2<String, NginxLogEvent>> output = new ArrayList<>();
        Collector<Tuple2<String, NginxLogEvent>> collector = new ListCollector<>(output);

        DimensionExtractor extractor = new DimensionExtractor.Builder()
                .enableIp()
                .build();

        NginxLogEvent event = createTestEvent();
        extractor.flatMap(event, collector);

        Set<String> keys = new HashSet<>();
        for (Tuple2<String, NginxLogEvent> tuple : output) {
            keys.add(tuple.f0);
        }

        assertTrue(keys.contains("ip:192.168.1.100"));
    }

    @Test
    public void testApiWhitelist() {
        List<Tuple2<String, NginxLogEvent>> output = new ArrayList<>();
        Collector<Tuple2<String, NginxLogEvent>> collector = new ListCollector<>(output);

        Set<String> whitelist = new HashSet<>();
        whitelist.add("/api/v1/users");
        whitelist.add("/api/v1/products");

        DimensionExtractor extractor = new DimensionExtractor.Builder()
                .enableApi()
                .enableApiStatus()
                .withApiWhitelist(whitelist)
                .build();

        NginxLogEvent allowedEvent = createTestEvent();
        allowedEvent.setPath("/api/v1/users");
        extractor.flatMap(allowedEvent, collector);

        NginxLogEvent blockedEvent = createTestEvent();
        blockedEvent.setPath("/api/internal/secret");
        extractor.flatMap(blockedEvent, collector);

        Set<String> keys = new HashSet<>();
        for (Tuple2<String, NginxLogEvent> tuple : output) {
            keys.add(tuple.f0);
        }

        assertTrue(keys.contains("api:/api/v1/users"));
        assertTrue(keys.contains("api_status:/api/v1/users|200"));
        assertFalse(keys.contains("api:/api/internal/secret"));
        assertFalse(keys.contains("api_status:/api/internal/secret|200"));
    }

    @Test
    public void testNullEvent() {
        List<Tuple2<String, NginxLogEvent>> output = new ArrayList<>();
        Collector<Tuple2<String, NginxLogEvent>> collector = new ListCollector<>(output);

        DimensionExtractor extractor = new DimensionExtractor.Builder()
                .enableAll()
                .build();

        extractor.flatMap(null, collector);

        assertTrue(output.isEmpty());
    }

    @Test
    public void testSelectiveDimensions() {
        List<Tuple2<String, NginxLogEvent>> output = new ArrayList<>();
        Collector<Tuple2<String, NginxLogEvent>> collector = new ListCollector<>(output);

        DimensionExtractor extractor = new DimensionExtractor.Builder()
                .enableAll()
                .enableStatus()
                .build();

        NginxLogEvent event = createTestEvent();
        extractor.flatMap(event, collector);

        Set<String> keys = new HashSet<>();
        for (Tuple2<String, NginxLogEvent> tuple : output) {
            keys.add(tuple.f0);
        }

        assertEquals(2, keys.size());
        assertTrue(keys.contains("all:total"));
        assertTrue(keys.contains("status:200"));
        assertFalse(keys.contains("api:/api/v1/users"));
    }

    private NginxLogEvent createTestEvent() {
        return NginxLogEvent.builder()
                .remoteAddr("192.168.1.100")
                .method("GET")
                .path("/api/v1/users")
                .uri("/api/v1/users?page=1")
                .status(200)
                .request("GET /api/v1/users?page=1 HTTP/1.1")
                .host("api.example.com")
                .requestTime(0.123)
                .timestamp(System.currentTimeMillis())
                .build();
    }

    private static class ListCollector<T> implements Collector<T> {
        private final List<T> list;

        public ListCollector(List<T> list) {
            this.list = list;
        }

        @Override
        public void collect(T record) {
            list.add(record);
        }

        @Override
        public void close() {
        }
    }
}
