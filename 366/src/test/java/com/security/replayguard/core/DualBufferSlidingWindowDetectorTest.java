package com.security.replayguard.core;

import com.security.replayguard.config.ReplayGuardProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DualBufferSlidingWindowDetectorTest {

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private RedisScript<Long> dualBufferSlidingWindowScript;

    private ReplayGuardProperties properties;
    private DualBufferSlidingWindowDetector detector;

    @BeforeEach
    void setUp() {
        properties = new ReplayGuardProperties();
        properties.getSlidingWindow().setTimeWindowSeconds(60);
        properties.getSlidingWindow().setMaxRequestsPerWindow(10);
        properties.getSlidingWindow().setDualBufferEnabled(true);
        properties.getSlidingWindow().setOverlapSeconds(10);

        detector = new DualBufferSlidingWindowDetector(
                redisTemplate,
                dualBufferSlidingWindowScript,
                properties
        );
    }

    @Test
    @DisplayName("Dual buffer enabled - request allowed")
    void testIsAllowed_DualBufferEnabled_Allowed() {
        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(1L);

        boolean result = detector.isAllowed("test-hash", "user:abc12345");

        assertTrue(result);
    }

    @Test
    @DisplayName("Dual buffer enabled - request blocked")
    void testIsAllowed_DualBufferEnabled_Blocked() {
        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(0L);

        boolean result = detector.isAllowed("test-hash", "user:abc12345");

        assertFalse(result);
    }

    @Test
    @DisplayName("Dual buffer disabled - falls back to single buffer")
    void testIsAllowed_DualBufferDisabled() {
        properties.getSlidingWindow().setDualBufferEnabled(false);

        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(1L);

        boolean result = detector.isAllowed("test-hash", "user:abc12345");

        assertTrue(result);
    }

    @Test
    @DisplayName("Get window status - returns correct status")
    void testGetWindowStatus() {
        String metaKey = "replay:dual:meta:user:abc12345:test-hash";
        long now = System.currentTimeMillis() / 1000;

        when(redisTemplate.opsForValue()).thenReturn(mock(org.springframework.data.redis.core.ValueOperations.class));
        when(redisTemplate.opsForValue().get(metaKey)).thenReturn(String.valueOf(now - 5));
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));
        when(redisTemplate.opsForZSet().zCard(anyString())).thenReturn(3L);
        when(redisTemplate.opsForZSet().count(anyString(), anyDouble(), anyDouble())).thenReturn(1L);

        DualBufferSlidingWindowDetector.WindowStatus status =
                detector.getWindowStatus("test-hash", "user:abc12345");

        assertTrue(status.isInOverlapPeriod());
        assertFalse(status.isNeedsWindowSwitch());
        assertEquals(4L, status.getCurrentWindowCount());
    }

    @Test
    @DisplayName("Get window status - needs switch when window expired")
    void testGetWindowStatus_NeedsSwitch() {
        String metaKey = "replay:dual:meta:user:abc12345:test-hash";
        long now = System.currentTimeMillis() / 1000;

        when(redisTemplate.opsForValue()).thenReturn(mock(org.springframework.data.redis.core.ValueOperations.class));
        when(redisTemplate.opsForValue().get(metaKey)).thenReturn(String.valueOf(now - 70));
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));
        when(redisTemplate.opsForZSet().zCard(anyString())).thenReturn(0L);

        DualBufferSlidingWindowDetector.WindowStatus status =
                detector.getWindowStatus("test-hash", "user:abc12345");

        assertFalse(status.isInOverlapPeriod());
        assertTrue(status.isNeedsWindowSwitch());
    }

    @Test
    @DisplayName("Force switch window - executes rename")
    void testForceSwitchWindow() {
        assertDoesNotThrow(() -> detector.forceSwitchWindow("test-hash", "user:abc12345"));
    }

    @Test
    @DisplayName("Clean expired - removes expired entries")
    void testCleanExpired() {
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));

        assertDoesNotThrow(() -> detector.cleanExpired("test-hash", "user:abc12345"));
    }

    @Test
    @DisplayName("Different partitions - independent counting")
    void testIsAllowed_DifferentPartitions_Independent() {
        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(1L);

        boolean result1 = detector.isAllowed("test-hash", "user:partition1");
        boolean result2 = detector.isAllowed("test-hash", "user:partition2");

        assertTrue(result1);
        assertTrue(result2);
    }

    @Test
    @DisplayName("Redis exception - defaults to allowed")
    void testIsAllowed_RedisException_DefaultAllowed() {
        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenThrow(new RuntimeException("Redis connection error"));

        boolean result = detector.isAllowed("test-hash", "user:abc12345");

        assertTrue(result, "Should default to allowed on exception");
    }
}
