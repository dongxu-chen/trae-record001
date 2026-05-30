package com.distid.tracking;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class IdLifecycleEventTest {

    @Test
    void shouldSerializeAndDeserialize() {
        IdLifecycleEvent original = IdLifecycleEvent.builder()
                .id(12345L)
                .readableId("20260527120000-ORDER-dc1-1a2b3c")
                .stage(IdLifecycleEvent.Stage.GENERATED)
                .bizTag("ORDER")
                .mode("snowflake")
                .timestamp(System.currentTimeMillis())
                .traceId("trace-abc-123")
                .spanId("span-def-456")
                .dcCode("dc1")
                .podName("distid-dc1-1")
                .detail("ID generated")
                .build();

        String serialized = original.toRedisValue();
        IdLifecycleEvent deserialized = IdLifecycleEvent.fromRedisValue(12345L, "20260527120000-ORDER-dc1-1a2b3c", serialized);

        assertEquals(original.getId(), deserialized.getId());
        assertEquals(original.getStage(), deserialized.getStage());
        assertEquals(original.getBizTag(), deserialized.getBizTag());
        assertEquals(original.getMode(), deserialized.getMode());
        assertEquals(original.getTraceId(), deserialized.getTraceId());
        assertEquals(original.getSpanId(), deserialized.getSpanId());
        assertEquals(original.getDcCode(), deserialized.getDcCode());
        assertEquals(original.getPodName(), deserialized.getPodName());
    }

    @Test
    void shouldHandleEmptyTraceContext() {
        IdLifecycleEvent event = IdLifecycleEvent.builder()
                .id(1L)
                .readableId("test")
                .stage(IdLifecycleEvent.Stage.ASSIGNED)
                .timestamp(1000L)
                .build();

        String serialized = event.toRedisValue();
        IdLifecycleEvent deserialized = IdLifecycleEvent.fromRedisValue(1L, "test", serialized);
        assertEquals(IdLifecycleEvent.Stage.ASSIGNED, deserialized.getStage());
    }
}
