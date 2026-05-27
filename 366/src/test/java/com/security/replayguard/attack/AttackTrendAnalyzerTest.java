package com.security.replayguard.attack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.HyperLogLogOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.data.redis.core.ZSetOperations;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AttackTrendAnalyzerTest {

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private HashOperations<String, Object, Object> hashOperations;

    @Mock
    private ValueOperations<String, String> valueOperations;

    @Mock
    private ZSetOperations<String, String> zSetOperations;

    @Mock
    private HyperLogLogOperations<String, String> hyperLogLogOperations;

    private AttackTrendAnalyzer attackTrendAnalyzer;

    @BeforeEach
    void setUp() {
        attackTrendAnalyzer = new AttackTrendAnalyzer(redisTemplate);

        when(redisTemplate.opsForHash()).thenReturn(hashOperations);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);
        when(redisTemplate.opsForHyperLogLog()).thenReturn(hyperLogLogOperations);
    }

    @Test
    @DisplayName("Record attack event - increments hourly stat")
    void testRecordAttackEvent_IncrementsHourlyStat() {
        String attackType = "nonce_replay";
        String ip = "192.168.1.1";
        String userId = "user-123";

        doNothing().when(hashOperations).increment(anyString(), anyString(), anyLong());
        when(hyperLogLogOperations.add(anyString(), anyString())).thenReturn(0L);
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        assertDoesNotThrow(() ->
                attackTrendAnalyzer.recordAttackEvent(attackType, ip, userId));

        verify(hashOperations, atLeastOnce()).increment(
                startsWith("replay:trend:hourly:"), eq(attackType), eq(1L));
        verify(hashOperations, atLeastOnce()).increment(
                startsWith("replay:trend:hourly:"), eq("total"), eq(1L));
    }

    @Test
    @DisplayName("Record attack event - increments daily stat")
    void testRecordAttackEvent_IncrementsDailyStat() {
        String attackType = "rate_limit_breach";
        String ip = "192.168.1.2";
        String userId = "user-456";

        doNothing().when(hashOperations).increment(anyString(), anyString(), anyLong());
        when(hyperLogLogOperations.add(anyString(), anyString())).thenReturn(0L);
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        assertDoesNotThrow(() ->
                attackTrendAnalyzer.recordAttackEvent(attackType, ip, userId));

        verify(hashOperations, atLeastOnce()).increment(
                startsWith("replay:trend:daily:"), eq(attackType), eq(1L));
    }

    @Test
    @DisplayName("Record attack event - updates summary")
    void testRecordAttackEvent_UpdatesSummary() {
        String attackType = "honeypot_triggered";
        String ip = "192.168.1.3";
        String userId = null;

        doNothing().when(hashOperations).increment(anyString(), anyString(), anyLong());
        when(hyperLogLogOperations.add(anyString(), anyString())).thenReturn(0L);
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        assertDoesNotThrow(() ->
                attackTrendAnalyzer.recordAttackEvent(attackType, ip, userId));

        verify(hashOperations, atLeastOnce()).increment(
                eq("replay:trend:summary"), eq(attackType), eq(1L));
        verify(hashOperations, atLeastOnce()).increment(
                eq("replay:trend:summary"), eq("total"), eq(1L));
    }

    @Test
    @DisplayName("Get hourly trend - returns correct data")
    void testGetHourlyTrend_ReturnsCorrectData() {
        int hours = 24;

        Map<Object, Object> hourData = new HashMap<>();
        hourData.put("total", "5");
        hourData.put("nonce_replay", "3");
        hourData.put("rate_limit_breach", "2");

        when(hashOperations.entries(startsWith("replay:trend:hourly:")))
                .thenReturn(hourData);
        when(hyperLogLogOperations.size(startsWith("replay:trend:hourly:")))
                .thenReturn(2L);

        AttackTrendAnalyzer.HourlyTrend trend =
                attackTrendAnalyzer.getHourlyTrend(hours);

        assertEquals(hours, trend.getHours());
        assertEquals(120L, trend.getTotalAttacks());
        assertEquals(5.0, trend.getAveragePerHour());
        assertEquals(5L, trend.getPeakHourAttacks());
    }

    @Test
    @DisplayName("Get hourly trend - empty data")
    void testGetHourlyTrend_EmptyData() {
        int hours = 12;

        when(hashOperations.entries(startsWith("replay:trend:hourly:")))
                .thenReturn(new HashMap<>());

        AttackTrendAnalyzer.HourlyTrend trend =
                attackTrendAnalyzer.getHourlyTrend(hours);

        assertEquals(0L, trend.getTotalAttacks());
        assertEquals(0.0, trend.getAveragePerHour());
    }

    @Test
    @DisplayName("Get daily trend - returns correct data")
    void testGetDailyTrend_ReturnsCorrectData() {
        int days = 7;

        Map<Object, Object> dayData = new HashMap<>();
        dayData.put("total", "50");

        when(hashOperations.entries(startsWith("replay:trend:daily:")))
                .thenReturn(dayData);
        when(hyperLogLogOperations.size(startsWith("replay:trend:daily:")))
                .thenReturn(3L);

        AttackTrendAnalyzer.DailyTrend trend =
                attackTrendAnalyzer.getDailyTrend(days);

        assertEquals(days, trend.getDays());
        assertEquals(350L, trend.getTotalAttacks());
        assertEquals(50.0, trend.getAveragePerDay());
    }

    @Test
    @DisplayName("Analyze time patterns - identifies peak hours")
    void testAnalyzeTimePatterns_IdentifiesPeakHours() {
        int hours = 24;

        Map<Object, Object> peakHourData = new HashMap<>();
        peakHourData.put("total", "20");

        Map<Object, Object> normalHourData = new HashMap<>();
        normalHourData.put("total", "5");

        long currentHour = System.currentTimeMillis() / 1000 / 3600;

        for (int i = 0; i < hours; i++) {
            long hourBucket = currentHour - i;
            String key = "replay:trend:hourly:" + hourBucket;

            if (i == 14) {
                when(hashOperations.entries(key)).thenReturn(peakHourData);
            } else {
                when(hashOperations.entries(key)).thenReturn(normalHourData);
            }
            when(hyperLogLogOperations.size(anyString())).thenReturn(1L);
        }

        AttackTrendAnalyzer.TimePatternAnalysis analysis =
                attackTrendAnalyzer.analyzeTimePatterns(hours);

        assertNotNull(analysis.getPeakHours());
        assertNotNull(analysis.getQuietHours());
        assertFalse(analysis.getPeakHours().isEmpty());
    }

    @Test
    @DisplayName("Get summary - returns aggregated stats")
    void testGetSummary_ReturnsAggregatedStats() {
        Map<Object, Object> summaryData = new HashMap<>();
        summaryData.put("total", "500");
        summaryData.put("nonce_replay", "200");
        summaryData.put("rate_limit_breach", "150");
        summaryData.put("lastUpdate", "1234567890");

        when(hashOperations.entries("replay:trend:summary")).thenReturn(summaryData);
        when(hashOperations.entries(startsWith("replay:trend:hourly:")))
                .thenReturn(new HashMap<>());
        when(hashOperations.entries(startsWith("replay:trend:daily:")))
                .thenReturn(new HashMap<>());

        AttackTrendAnalyzer.AttackSummary summary =
                attackTrendAnalyzer.getSummary();

        assertEquals(500L, summary.getTotalAttacks());
        assertEquals(1234567890L, summary.getLastUpdateTime());
        assertEquals(2, summary.getAttackBreakdown().size());
    }

    @Test
    @DisplayName("Get hourly trend - calculates standard deviation")
    void testGetHourlyTrend_CalculatesStdDeviation() {
        int hours = 3;

        Map<Object, Object> hourData1 = new HashMap<>();
        hourData1.put("total", "10");
        Map<Object, Object> hourData2 = new HashMap<>();
        hourData2.put("total", "20");
        Map<Object, Object> hourData3 = new HashMap<>();
        hourData3.put("total", "30");

        long currentHour = System.currentTimeMillis() / 1000 / 3600;

        when(hashOperations.entries("replay:trend:hourly:" + (currentHour - 2)))
                .thenReturn(hourData1);
        when(hashOperations.entries("replay:trend:hourly:" + (currentHour - 1)))
                .thenReturn(hourData2);
        when(hashOperations.entries("replay:trend:hourly:" + currentHour))
                .thenReturn(hourData3);
        when(hyperLogLogOperations.size(anyString())).thenReturn(1L);

        AttackTrendAnalyzer.HourlyTrend trend =
                attackTrendAnalyzer.getHourlyTrend(hours);

        assertEquals(60L, trend.getTotalAttacks());
        assertTrue(trend.getStdDeviation() > 0);
    }
}
