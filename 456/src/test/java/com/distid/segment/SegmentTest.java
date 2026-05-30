package com.distid.segment;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SegmentTest {

    @Test
    void shouldReturnSequentialIds() {
        Segment segment = new Segment("test", 1000, 1000);
        long id1 = segment.nextId();
        long id2 = segment.nextId();
        assertEquals(1, id1);
        assertEquals(2, id2);
    }

    @Test
    void shouldReturnMinusOneWhenExhausted() {
        Segment segment = new Segment("test", 2, 2);
        segment.nextId();
        segment.nextId();
        long id = segment.nextId();
        assertEquals(-1, id);
    }

    @Test
    void shouldDetectExhaustion() {
        Segment segment = new Segment("test", 2, 2);
        assertFalse(segment.isExhausted());
        segment.nextId();
        segment.nextId();
        assertTrue(segment.isExhausted());
    }

    @Test
    void shouldCalculateUsage() {
        Segment segment = new Segment("test", 1000, 1000);
        assertEquals(0.0, segment.usage(), 0.01);
        segment.nextId();
        assertTrue(segment.usage() > 0);
    }
}
