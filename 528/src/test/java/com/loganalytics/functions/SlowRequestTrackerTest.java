package com.loganalytics.functions;

import com.loganalytics.model.NginxLogEvent;
import com.loganalytics.model.SlowRequestEvent;
import com.loganalytics.model.TraceSpan;
import org.apache.flink.streaming.api.operators.StreamFlatMap;
import org.apache.flink.streaming.runtime.streamrecord.StreamRecord;
import org.apache.flink.streaming.util.KeyedOneInputStreamOperatorTestHarness;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.Queue;

import static org.junit.Assert.*;

public class SlowRequestTrackerTest {

    private KeyedOneInputStreamOperatorTestHarness<String, NginxLogEvent, SlowRequestEvent> testHarness;
    private SlowRequestTracker tracker;

    @Before
    public void setUp() throws Exception {
        tracker = new SlowRequestTracker(500.0, 0.7, 100);
        testHarness = new KeyedOneInputStreamOperatorTestHarness<>(
                new StreamFlatMap(tracker),
                event -> "api:" + event.getPath(),
                org.apache.flink.api.common.typeinfo.TypeInformation.of(String.class),
                org.apache.flink.api.common.typeinfo.TypeInformation.of(NginxLogEvent.class),
                org.apache.flink.api.common.typeinfo.TypeInformation.of(SlowRequestEvent.class)
        );
        testHarness.open();
    }

    @After
    public void tearDown() throws Exception {
        testHarness.close();
    }

    @Test
    public void testSlowRequestDetected() throws Exception {
        NginxLogEvent slowEvent = createEvent("/api/v1/users", 1000.0, 800.0, 200);
        testHarness.processElement(new StreamRecord<>(slowEvent));

        Queue<?> output = testHarness.getOutput();
        assertEquals(1, output.size());
    }

    @Test
    public void testFastRequestNotDetected() throws Exception {
        NginxLogEvent fastEvent = createEvent("/api/v1/users", 50.0, 30.0, 200);
        testHarness.processElement(new StreamRecord<>(fastEvent));

        Queue<?> output = testHarness.getOutput();
        assertTrue(output.isEmpty());
    }

    @Test
    public void testUpstreamSlowClassification() throws Exception {
        NginxLogEvent event = createEvent("/api/v1/data", 1000.0, 900.0, 200);
        testHarness.processElement(new StreamRecord<>(event));

        Queue<StreamRecord<SlowRequestEvent>> output = (Queue) testHarness.getOutput();
        SlowRequestEvent slowEvent = output.poll().getValue();

        assertTrue(slowEvent.isUpstreamSlow());
        assertEquals("UPSTREAM_SLOW", slowEvent.getSlowReason());
    }

    @Test
    public void testSelfSlowClassification() throws Exception {
        NginxLogEvent event = createEvent("/api/v1/data", 1000.0, 100.0, 200);
        testHarness.processElement(new StreamRecord<>(event));

        Queue<StreamRecord<SlowRequestEvent>> output = (Queue) testHarness.getOutput();
        SlowRequestEvent slowEvent = output.poll().getValue();

        assertTrue(slowEvent.isSelfSlow());
        assertEquals("SELF_SLOW", slowEvent.getSlowReason());
    }

    @Test
    public void testBothSlowClassification() throws Exception {
        NginxLogEvent event = createEvent("/api/v1/data", 1000.0, 600.0, 200);
        testHarness.processElement(new StreamRecord<>(event));

        Queue<StreamRecord<SlowRequestEvent>> output = (Queue) testHarness.getOutput();
        SlowRequestEvent slowEvent = output.poll().getValue();

        assertTrue(slowEvent.isUpstreamSlow());
        assertTrue(slowEvent.isSelfSlow());
        assertEquals("BOTH_SLOW", slowEvent.getSlowReason());
    }

    @Test
    public void testTraceSpanGeneration() throws Exception {
        NginxLogEvent event = createEvent("/api/v1/data", 1000.0, 600.0, 200);
        testHarness.processElement(new StreamRecord<>(event));

        Queue<StreamRecord<SlowRequestEvent>> output = (Queue) testHarness.getOutput();
        SlowRequestEvent slowEvent = output.poll().getValue();

        assertNotNull(slowEvent.getDownstreamSpans());
        assertEquals(2, slowEvent.getDownstreamSpans().size());

        TraceSpan upstreamSpan = slowEvent.getDownstreamSpans().get(0);
        assertEquals("upstream", upstreamSpan.getServiceName());
        assertEquals(600.0, upstreamSpan.getDuration(), 0.01);

        TraceSpan selfSpan = slowEvent.getDownstreamSpans().get(1);
        assertEquals("nginx", selfSpan.getServiceName());
        assertEquals(400.0, selfSpan.getDuration(), 0.01);
    }

    @Test
    public void testDynamicThresholdWithProfile() throws Exception {
        for (int i = 0; i < 50; i++) {
            NginxLogEvent normalEvent = createEvent("/api/v1/health", 10.0 + i * 0.5, 5.0, 200);
            testHarness.processElement(new StreamRecord<>(normalEvent));
        }

        Queue<?> output1 = testHarness.getOutput();
        assertTrue(output1.isEmpty());

        NginxLogEvent slightlySlowEvent = createEvent("/api/v1/health", 100.0, 50.0, 200);
        testHarness.processElement(new StreamRecord<>(slightlySlowEvent));

        Queue<?> output2 = testHarness.getOutput();
        assertFalse(output2.isEmpty());
    }

    @Test
    public void testSelfProcessTimeCalculation() throws Exception {
        NginxLogEvent event = createEvent("/api/v1/test", 800.0, 300.0, 200);
        testHarness.processElement(new StreamRecord<>(event));

        Queue<StreamRecord<SlowRequestEvent>> output = (Queue) testHarness.getOutput();
        SlowRequestEvent slowEvent = output.poll().getValue();

        assertEquals(800.0, slowEvent.getRequestTime(), 0.01);
        assertEquals(300.0, slowEvent.getUpstreamResponseTime(), 0.01);
        assertEquals(500.0, slowEvent.getSelfProcessTime(), 0.01);
    }

    private NginxLogEvent createEvent(String path, double requestTime, double upstreamTime, int status) {
        return NginxLogEvent.builder()
                .remoteAddr("10.0.0.1")
                .method("GET")
                .path(path)
                .uri(path)
                .status(status)
                .requestTime(requestTime)
                .upstreamResponseTime(upstreamTime)
                .upstreamStatus("200")
                .host("api.example.com")
                .timestamp(System.currentTimeMillis())
                .build();
    }
}
