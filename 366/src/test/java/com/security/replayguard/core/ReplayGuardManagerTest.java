package com.security.replayguard.core;

import com.security.replayguard.attack.ActiveDefenseService;
import com.security.replayguard.attack.AttackTraceService;
import com.security.replayguard.attack.AttackTrendAnalyzer;
import com.security.replayguard.config.ReplayGuardProperties;
import com.security.replayguard.model.RequestFeature;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.data.redis.core.script.RedisScript;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ReplayGuardManagerTest {

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private RedisScript<Long> slidingWindowScript;

    @Mock
    private RedisScript<Long> dualBufferSlidingWindowScript;

    @Mock
    private RedisScript<Long> nonceCheckAndSetScript;

    @Mock
    private RedisScript<Long> honeypotScript;

    @Mock
    private RedisScript<Long> dynamicHoneypotScript;

    @Mock
    private RedisScript<Long> distributedCounterScript;

    @Mock
    private ZSetOperations<String, String> zSetOperations;

    private ReplayGuardProperties properties;
    private ReplayGuardManager replayGuardManager;
    private AttackTraceService attackTraceService;
    private ActiveDefenseService activeDefenseService;
    private AttackTrendAnalyzer attackTrendAnalyzer;

    @BeforeEach
    void setUp() {
        properties = new ReplayGuardProperties();
        properties.setNonceExpireSeconds(300);
        properties.getSlidingWindow().setTimeWindowSeconds(60);
        properties.getSlidingWindow().setMaxRequestsPerWindow(10);
        properties.getSlidingWindow().setDualBufferEnabled(true);
        properties.getSlidingWindow().setOverlapSeconds(10);
        properties.getHoneypot().setEnabled(true);
        properties.getHoneypot().setSlowThresholdMs(2000);
        properties.getHoneypot().setMaxSlowRequests(5);
        properties.getHoneypot().setBlockDurationSeconds(600);
        properties.getHoneypot().setDynamicThresholdEnabled(true);

        RequestHasher requestHasher = new RequestHasher();
        SlidingWindowDetector slidingWindowDetector = new SlidingWindowDetector(redisTemplate, slidingWindowScript, properties);
        DualBufferSlidingWindowDetector dualBufferDetector = new DualBufferSlidingWindowDetector(redisTemplate, dualBufferSlidingWindowScript, properties);
        NonceDetector nonceDetector = new NonceDetector(redisTemplate, nonceCheckAndSetScript, properties, requestHasher);
        DistributedCounter distributedCounter = new DistributedCounter(redisTemplate, distributedCounterScript);
        HoneypotDetector honeypotDetector = new HoneypotDetector(redisTemplate, honeypotScript, properties);
        DynamicHoneypotDetector dynamicHoneypotDetector = new DynamicHoneypotDetector(redisTemplate, dynamicHoneypotScript, properties);
        dynamicHoneypotDetector.init();
        ConsistentHashRouter consistentHashRouter = new ConsistentHashRouter(properties);
        consistentHashRouter.init();

        attackTraceService = new AttackTraceService(redisTemplate, properties, requestHasher);
        activeDefenseService = new ActiveDefenseService(redisTemplate, properties, attackTraceService);
        attackTrendAnalyzer = new AttackTrendAnalyzer(redisTemplate);

        replayGuardManager = new ReplayGuardManager(
                requestHasher,
                slidingWindowDetector,
                dualBufferDetector,
                nonceDetector,
                distributedCounter,
                honeypotDetector,
                dynamicHoneypotDetector,
                consistentHashRouter,
                properties,
                attackTraceService,
                activeDefenseService,
                attackTrendAnalyzer
        );
    }

    @Test
    @DisplayName("Check request - valid request should be allowed")
    void testCheckRequest_ValidRequest() {
        RequestFeature feature = createSampleFeature();

        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.execute(eq(nonceCheckAndSetScript), anyList(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.execute(eq(distributedCounterScript), anyList(), anyString(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.hasKey(anyString())).thenReturn(false);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequest(feature);

        assertTrue(result.isAllowed());
        assertFalse(result.isBlocked());
        assertNull(result.getReason());
        assertNotNull(result.getPartitionKey());
    }

    @Test
    @DisplayName("Check request - blocked by honeypot")
    void testCheckRequest_BlockedByHoneypot() {
        RequestFeature feature = createSampleFeature();

        when(redisTemplate.hasKey(anyString())).thenReturn(true);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequest(feature);

        assertFalse(result.isAllowed());
        assertTrue(result.isBlocked());
        assertEquals("CLIENT_BLOCKED_BY_HONEYPOT", result.getReason());
    }

    @Test
    @DisplayName("Check request - blocked by invalid timestamp")
    void testCheckRequest_InvalidTimestamp() {
        RequestFeature feature = createSampleFeature();
        feature.setTimestamp("9999999999999");

        when(redisTemplate.hasKey(anyString())).thenReturn(false);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequest(feature);

        assertFalse(result.isAllowed());
        assertTrue(result.isBlocked());
        assertEquals("INVALID_TIMESTAMP", result.getReason());
    }

    @Test
    @DisplayName("Check request - blocked by nonce replay")
    void testCheckRequest_NonceReplay() {
        RequestFeature feature = createSampleFeature();

        when(redisTemplate.hasKey(anyString())).thenReturn(false);
        when(redisTemplate.execute(eq(nonceCheckAndSetScript), anyList(), anyString(), anyString()))
                .thenReturn(0L);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequest(feature);

        assertFalse(result.isAllowed());
        assertTrue(result.isBlocked());
        assertEquals("NONCE_REPLAY_DETECTED", result.getReason());
    }

    @Test
    @DisplayName("Check request - blocked by sliding window limit")
    void testCheckRequest_SlidingWindowLimit() {
        RequestFeature feature = createSampleFeature();

        when(redisTemplate.hasKey(anyString())).thenReturn(false);
        when(redisTemplate.execute(eq(nonceCheckAndSetScript), anyList(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(0L);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequest(feature);

        assertFalse(result.isAllowed());
        assertTrue(result.isBlocked());
        assertEquals("SLIDING_WINDOW_LIMIT_EXCEEDED", result.getReason());
    }

    @Test
    @DisplayName("Check request - with user ID sets partition key")
    void testCheckRequest_WithUserId() {
        RequestFeature feature = createSampleFeature();
        feature.setUserId("user-123");

        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.execute(eq(nonceCheckAndSetScript), anyList(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.execute(eq(distributedCounterScript), anyList(), anyString(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.hasKey(anyString())).thenReturn(false);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequest(feature);

        assertTrue(result.isAllowed());
        assertNotNull(result.getPartitionKey());
        assertTrue(result.getPartitionKey().startsWith("user:"));
    }

    @Test
    @DisplayName("Check request with honeypot - slow request recorded")
    void testCheckRequestWithHoneypot_SlowRequest() {
        RequestFeature feature = createSampleFeature();

        when(redisTemplate.execute(eq(dualBufferSlidingWindowScript), anyList(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.execute(eq(nonceCheckAndSetScript), anyList(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.execute(eq(distributedCounterScript), anyList(), anyString(), anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.hasKey(anyString())).thenReturn(false);
        when(redisTemplate.execute(eq(dynamicHoneypotScript), anyList(), anyString(), anyString(),
                anyString(), anyString()))
                .thenReturn(1L);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);

        ReplayGuardManager.DetectionResult result = replayGuardManager.checkRequestWithHoneypot(feature, 5000);

        assertTrue(result.isAllowed());
        assertFalse(result.isBlocked());
    }

    @Test
    @DisplayName("Get node for hash")
    void testGetNodeForHash() {
        String node = replayGuardManager.getNodeForHash("test-hash");

        assertNotNull(node);
        assertTrue(properties.getConsistentHash().getNodes().contains(node));
    }

    private RequestFeature createSampleFeature() {
        Map<String, String> params = new HashMap<>();
        params.put("key1", "value1");

        return RequestFeature.builder()
                .requestPath("/api/test")
                .method("POST")
                .queryParams(params)
                .bodyHash("abc123")
                .timestamp(String.valueOf(System.currentTimeMillis() / 1000))
                .nonce("test-nonce-" + System.nanoTime())
                .deviceFingerprint("device-fp-123")
                .ipAddress("192.168.1.1")
                .userAgent("Mozilla/5.0")
                .build();
    }
}
