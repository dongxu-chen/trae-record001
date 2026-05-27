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

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class DynamicHoneypotDetectorTest {

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private RedisScript<Long> dynamicHoneypotScript;

    private ReplayGuardProperties properties;
    private DynamicHoneypotDetector detector;

    @BeforeEach
    void setUp() {
        properties = new ReplayGuardProperties();
        properties.getHoneypot().setEnabled(true);
        properties.getHoneypot().setSlowThresholdMs(2000);
        properties.getHoneypot().setMaxSlowRequests(5);
        properties.getHoneypot().setBlockDurationSeconds(600);
        properties.getHoneypot().setDynamicThresholdEnabled(true);
        properties.getHoneypot().setPercentile(0.95);
        properties.getHoneypot().setMinThresholdMs(500);
        properties.getHoneypot().setMaxThresholdMs(10000);
        properties.getHoneypot().setHistoryWindowMinutes(60);

        detector = new DynamicHoneypotDetector(
                redisTemplate,
                dynamicHoneypotScript,
                properties
        );
        detector.init();
    }

    @Test
    @DisplayName("Check - honeypot disabled returns not slow, not blocked")
    void testCheck_HoneypotDisabled() {
        properties.getHoneypot().setEnabled(false);

        DynamicHoneypotDetector.HoneypotResult result = detector.check("client-1", 5000);

        assertFalse(result.isSlowRequest());
        assertFalse(result.isBlocked());
    }

    @Test
    @DisplayName("Check - normal request returns not slow")
    void testCheck_NormalRequest() {
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));
        when(redisTemplate.execute(eq(dynamicHoneypotScript), anyList(), anyString(), anyString(),
                anyString(), anyString()))
                .thenReturn(1L);

        DynamicHoneypotDetector.HoneypotResult result = detector.check("client-1", 500);

        assertFalse(result.isSlowRequest());
        assertFalse(result.isBlocked());
    }

    @Test
    @DisplayName("Check - slow request returns isSlow=true")
    void testCheck_SlowRequest() {
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));
        when(redisTemplate.execute(eq(dynamicHoneypotScript), anyList(), anyString(), anyString(),
                anyString(), anyString()))
                .thenReturn(1L);

        DynamicHoneypotDetector.HoneypotResult result = detector.check("client-1", 5000);

        assertTrue(result.isSlowRequest());
        assertFalse(result.isBlocked());
    }

    @Test
    @DisplayName("Check - blocked client returns isBlocked=true")
    void testCheck_BlockedClient() {
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));
        when(redisTemplate.execute(eq(dynamicHoneypotScript), anyList(), anyString(), anyString(),
                anyString(), anyString()))
                .thenReturn(2L);

        DynamicHoneypotDetector.HoneypotResult result = detector.check("client-1", 500);

        assertTrue(result.isBlocked());
    }

    @Test
    @DisplayName("Check - uses global threshold when no client-specific threshold")
    void testCheck_UsesGlobalThreshold() {
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));
        when(redisTemplate.opsForValue()).thenReturn(mock(org.springframework.data.redis.core.ValueOperations.class));
        when(redisTemplate.opsForValue().get(anyString())).thenReturn(null);
        when(redisTemplate.execute(eq(dynamicHoneypotScript), anyList(), anyString(), anyString(),
                anyString(), anyString()))
                .thenReturn(1L);

        detector.check("client-1", 100);

        long globalThreshold = detector.getGlobalThreshold();
        assertEquals(2000, globalThreshold);
    }

    @Test
    @DisplayName("Is blocked - returns true when blocked key exists")
    void testIsBlocked_ReturnsTrue() {
        when(redisTemplate.hasKey(anyString())).thenReturn(true);

        boolean blocked = detector.isBlocked("client-1");

        assertTrue(blocked);
    }

    @Test
    @DisplayName("Is blocked - returns false when blocked key not exists")
    void testIsBlocked_ReturnsFalse() {
        when(redisTemplate.hasKey(anyString())).thenReturn(false);

        boolean blocked = detector.isBlocked("client-1");

        assertFalse(blocked);
    }

    @Test
    @DisplayName("Unblock - deletes keys")
    void testUnblock_DeletesKeys() {
        doNothing().when(redisTemplate).delete(anyString());

        assertDoesNotThrow(() -> detector.unblock("client-1"));
    }

    @Test
    @DisplayName("Get threshold stats - returns correct stats")
    void testGetThresholdStats() {
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));
        when(redisTemplate.opsForZSet().zCard(anyString())).thenReturn(100L);

        DynamicHoneypotDetector.ThresholdStats stats = detector.getThresholdStats("client-1");

        assertEquals(2000, stats.getGlobalThreshold());
        assertEquals(2000, stats.getClientThreshold());
        assertTrue(stats.isDynamicEnabled());
        assertEquals(100, stats.getHistorySampleCount());
    }

    @Test
    @DisplayName("Get current threshold - returns global threshold")
    void testGetCurrentThreshold() {
        long threshold = detector.getCurrentThreshold("client-1");

        assertEquals(2000, threshold);
    }

    @Test
    @DisplayName("Get global threshold - returns initial threshold")
    void testGetGlobalThreshold() {
        long threshold = detector.getGlobalThreshold();

        assertEquals(2000, threshold);
    }

    @Test
    @DisplayName("Redis exception - graceful handling")
    void testCheck_RedisException_GracefulHandling() {
        when(redisTemplate.opsForZSet()).thenReturn(mock(org.springframework.data.redis.core.ZSetOperations.class));
        when(redisTemplate.execute(eq(dynamicHoneypotScript), anyList(), anyString(), anyString(),
                anyString(), anyString()))
                .thenThrow(new RuntimeException("Redis error"));

        DynamicHoneypotDetector.HoneypotResult result = detector.check("client-1", 500);

        assertFalse(result.isSlowRequest());
        assertFalse(result.isBlocked());
    }

    @Test
    @DisplayName("Is blocked - Redis exception returns false")
    void testIsBlocked_RedisException_ReturnsFalse() {
        when(redisTemplate.hasKey(anyString())).thenThrow(new RuntimeException("Redis error"));

        boolean blocked = detector.isBlocked("client-1");

        assertFalse(blocked);
    }

    @Test
    @DisplayName("Get slow request count - returns count")
    void testGetSlowRequestCount() {
        when(redisTemplate.opsForValue()).thenReturn(mock(org.springframework.data.redis.core.ValueOperations.class));
        when(redisTemplate.opsForValue().get(anyString())).thenReturn("3");

        long count = detector.getSlowRequestCount("client-1");

        assertEquals(3, count);
    }

    @Test
    @DisplayName("Get slow request count - Redis exception returns 0")
    void testGetSlowRequestCount_RedisException_ReturnsZero() {
        when(redisTemplate.opsForValue()).thenThrow(new RuntimeException("Redis error"));

        long count = detector.getSlowRequestCount("client-1");

        assertEquals(0, count);
    }
}
