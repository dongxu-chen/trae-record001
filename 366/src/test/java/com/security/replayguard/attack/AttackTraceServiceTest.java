package com.security.replayguard.attack;

import com.security.replayguard.config.ReplayGuardProperties;
import com.security.replayguard.core.RequestHasher;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.data.redis.core.ZSetOperations;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AttackTraceServiceTest {

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private HashOperations<String, Object, Object> hashOperations;

    @Mock
    private ValueOperations<String, String> valueOperations;

    @Mock
    private ZSetOperations<String, String> zSetOperations;

    private ReplayGuardProperties properties;
    private RequestHasher requestHasher;
    private AttackTraceService attackTraceService;

    @BeforeEach
    void setUp() {
        properties = new ReplayGuardProperties();
        requestHasher = new RequestHasher();
        attackTraceService = new AttackTraceService(redisTemplate, properties, requestHasher);

        when(redisTemplate.opsForHash()).thenReturn(hashOperations);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);
    }

    @Test
    @DisplayName("Record attack - creates attack log")
    void testRecordAttack_CreatesLog() {
        AttackEvent event = AttackEvent.builder()
                .attackType("nonce_replay")
                .ipAddress("192.168.1.1")
                .userId("user-123")
                .deviceFingerprint("device-fp")
                .requestPath("/api/test")
                .build();

        doNothing().when(hashOperations).putAll(anyString(), anyMap());
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        assertDoesNotThrow(() -> attackTraceService.recordAttack(event));

        assertNotNull(event.getAttackId());
        assertTrue(event.getAttackId().startsWith("ATT-"));
    }

    @Test
    @DisplayName("Record attack - increments IP attack count")
    void testRecordAttack_IncrementsIpCount() {
        AttackEvent event = AttackEvent.builder()
                .attackType("nonce_replay")
                .ipAddress("192.168.1.1")
                .requestPath("/api/test")
                .build();

        doNothing().when(hashOperations).putAll(anyString(), anyMap());
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        attackTraceService.recordAttack(event);

        verify(hashOperations, atLeastOnce()).increment(startsWith("replay:attack:ip:"), eq("nonce_replay"), eq(1L));
        verify(hashOperations, atLeastOnce()).increment(startsWith("replay:attack:ip:"), eq("total"), eq(1L));
    }

    @Test
    @DisplayName("Record attack - increments user attack count")
    void testRecordAttack_IncrementsUserCount() {
        AttackEvent event = AttackEvent.builder()
                .attackType("rate_limit_breach")
                .userId("user-456")
                .requestPath("/api/test")
                .build();

        doNothing().when(hashOperations).putAll(anyString(), anyMap());
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        attackTraceService.recordAttack(event);

        verify(hashOperations, atLeastOnce()).increment(startsWith("replay:attack:user:"), eq("rate_limit_breach"), eq(1L));
        verify(hashOperations, atLeastOnce()).increment(startsWith("replay:attack:user:"), eq("total"), eq(1L));
    }

    @Test
    @DisplayName("Get IP attack stats - returns correct stats")
    void testGetIpAttackStats_ReturnsCorrectStats() {
        String ip = "192.168.1.1";
        Map<Object, Object> hashData = new HashMap<>();
        hashData.put("total", "5");
        hashData.put("nonce_replay", "3");
        hashData.put("lastAttackTime", "1234567890");

        when(hashOperations.entries("replay:attack:ip:" + ip)).thenReturn(hashData);

        AttackTraceService.AttackSourceStats stats = attackTraceService.getIpAttackStats(ip);

        assertEquals(ip, stats.getIpAddress());
        assertEquals(5, stats.getTotalAttacks());
        assertEquals(1234567890L, stats.getLastAttackTime());
        assertEquals(1, stats.getAttackBreakdown().size());
        assertEquals(3L, stats.getAttackBreakdown().get("nonce_replay"));
    }

    @Test
    @DisplayName("Get IP attack stats - no data returns empty stats")
    void testGetIpAttackStats_NoData_ReturnsEmpty() {
        String ip = "10.0.0.1";

        when(hashOperations.entries("replay:attack:ip:" + ip)).thenReturn(new HashMap<>());

        AttackTraceService.AttackSourceStats stats = attackTraceService.getIpAttackStats(ip);

        assertEquals(ip, stats.getIpAddress());
        assertEquals(0, stats.getTotalAttacks());
    }

    @Test
    @DisplayName("Get user attack stats - returns correct stats")
    void testGetUserAttackStats_ReturnsCorrectStats() {
        String userId = "user-123";
        Map<Object, Object> hashData = new HashMap<>();
        hashData.put("total", "10");
        hashData.put("sliding_window_breach", "7");
        hashData.put("lastAttackTime", "1234567890");

        when(hashOperations.entries("replay:attack:user:" + userId)).thenReturn(hashData);

        AttackTraceService.UserAttackStats stats = attackTraceService.getUserAttackStats(userId);

        assertEquals(userId, stats.getUserId());
        assertEquals(10, stats.getTotalAttacks());
        assertEquals(1234567890L, stats.getLastAttackTime());
    }

    @Test
    @DisplayName("Get top attack IPs - returns sorted list")
    void testGetTopAttackIps_ReturnsSortedList() {
        Set<String> ips = new LinkedHashSet<>(Arrays.asList("192.168.1.1", "192.168.1.2"));

        when(zSetOperations.reverseRange(eq("replay:attack:sources"), eq(0L), eq(4L))).thenReturn(ips);

        Map<Object, Object> hashData1 = new HashMap<>();
        hashData1.put("total", "8");
        Map<Object, Object> hashData2 = new HashMap<>();
        hashData2.put("total", "3");

        when(hashOperations.entries("replay:attack:ip:192.168.1.1")).thenReturn(hashData1);
        when(hashOperations.entries("replay:attack:ip:192.168.1.2")).thenReturn(hashData2);

        List<AttackTraceService.AttackSourceStats> topIps = attackTraceService.getTopAttackIps(5);

        assertEquals(2, topIps.size());
        assertEquals(8, topIps.get(0).getTotalAttacks());
        assertEquals(3, topIps.get(1).getTotalAttacks());
    }

    @Test
    @DisplayName("Get recent attacks - returns sorted events")
    void testGetRecentAttacks_ReturnsSortedEvents() {
        Set<String> keys = new HashSet<>(Arrays.asList(
                "replay:attack:log:ATT-1", "replay:attack:log:ATT-2"
        ));

        when(redisTemplate.keys("replay:attack:log:ATT-*")).thenReturn(keys);

        Map<Object, Object> attack1 = new HashMap<>();
        attack1.put("attackId", "ATT-1");
        attack1.put("attackType", "nonce_replay");
        attack1.put("ipAddress", "192.168.1.1");
        attack1.put("timestamp", "1000000002");

        Map<Object, Object> attack2 = new HashMap<>();
        attack2.put("attackId", "ATT-2");
        attack2.put("attackType", "rate_limit_breach");
        attack2.put("ipAddress", "192.168.1.2");
        attack2.put("timestamp", "1000000001");

        when(hashOperations.entries("replay:attack:log:ATT-1")).thenReturn(attack1);
        when(hashOperations.entries("replay:attack:log:ATT-2")).thenReturn(attack2);

        List<AttackEvent> attacks = attackTraceService.getRecentAttacks(10);

        assertEquals(2, attacks.size());
        assertEquals("ATT-1", attacks.get(0).getAttackId());
        assertEquals("ATT-2", attacks.get(1).getAttackId());
    }

    @Test
    @DisplayName("Record attack - null IP doesn't increment IP count")
    void testRecordAttack_NullIp_DoesNotIncrementIpCount() {
        AttackEvent event = AttackEvent.builder()
                .attackType("nonce_replay")
                .requestPath("/api/test")
                .build();

        doNothing().when(hashOperations).putAll(anyString(), anyMap());
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        attackTraceService.recordAttack(event);

        verify(hashOperations, never()).increment(startsWith("replay:attack:ip:"), anyString(), anyLong());
    }
}
