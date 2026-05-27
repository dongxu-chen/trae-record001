package com.security.replayguard.attack;

import com.security.replayguard.config.ReplayGuardProperties;
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

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ActiveDefenseServiceTest {

    @Mock
    private StringRedisTemplate redisTemplate;

    @Mock
    private HashOperations<String, Object, Object> hashOperations;

    @Mock
    private ValueOperations<String, String> valueOperations;

    @Mock
    private ZSetOperations<String, String> zSetOperations;

    private ReplayGuardProperties properties;
    private AttackTraceService attackTraceService;
    private ActiveDefenseService activeDefenseService;

    @BeforeEach
    void setUp() {
        properties = new ReplayGuardProperties();
        attackTraceService = mock(AttackTraceService.class);
        activeDefenseService = new ActiveDefenseService(redisTemplate, properties, attackTraceService);

        when(redisTemplate.opsForHash()).thenReturn(hashOperations);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOperations);
    }

    @Test
    @DisplayName("Check and lock account - not locked, below threshold")
    void testCheckAndLockAccount_NotLocked() {
        String userId = "user-123";
        String ipAddress = "192.168.1.1";

        when(redisTemplate.hasKey(anyString())).thenReturn(false);

        AttackTraceService.UserAttackStats userStats = new AttackTraceService.UserAttackStats();
        userStats.setTotalAttacks(5);
        when(attackTraceService.getUserAttackStats(userId)).thenReturn(userStats);

        AttackTraceService.AttackSourceStats ipStats = new AttackTraceService.AttackSourceStats();
        ipStats.setTotalAttacks(10);
        when(attackTraceService.getIpAttackStats(ipAddress)).thenReturn(ipStats);

        ActiveDefenseService.LockResult result =
                activeDefenseService.checkAndLockAccount(userId, ipAddress);

        assertFalse(result.isLocked());
        assertNull(result.getReason());
    }

    @Test
    @DisplayName("Check and lock account - account already locked")
    void testCheckAndLockAccount_AccountLocked() {
        String userId = "user-locked";
        String ipAddress = "192.168.1.2";

        when(redisTemplate.hasKey("replay:lock:account:" + userId)).thenReturn(true);
        when(hashOperations.get("replay:lock:account:" + userId, "reason"))
                .thenReturn("Attack threshold exceeded");

        ActiveDefenseService.LockResult result =
                activeDefenseService.checkAndLockAccount(userId, ipAddress);

        assertTrue(result.isLocked());
        assertEquals("Attack threshold exceeded", result.getReason());
    }

    @Test
    @DisplayName("Check and lock account - IP already locked")
    void testCheckAndLockAccount_IpLocked() {
        String userId = "user-ip-locked";
        String ipAddress = "192.168.1.3";

        when(redisTemplate.hasKey("replay:lock:account:" + userId)).thenReturn(false);
        when(redisTemplate.hasKey("replay:lock:ip:" + ipAddress)).thenReturn(true);
        when(hashOperations.get("replay:lock:ip:" + ipAddress, "reason"))
                .thenReturn("IP attack threshold exceeded");

        ActiveDefenseService.LockResult result =
                activeDefenseService.checkAndLockAccount(userId, ipAddress);

        assertTrue(result.isLocked());
        assertEquals("IP attack threshold exceeded", result.getReason());
    }

    @Test
    @DisplayName("Check and lock account - user attack threshold exceeded")
    void testCheckAndLockAccount_UserThresholdExceeded() {
        String userId = "user-threshold";
        String ipAddress = "192.168.1.4";

        when(redisTemplate.hasKey(anyString())).thenReturn(false);

        AttackTraceService.UserAttackStats userStats = new AttackTraceService.UserAttackStats();
        userStats.setTotalAttacks(15);
        when(attackTraceService.getUserAttackStats(userId)).thenReturn(userStats);

        AttackTraceService.AttackSourceStats ipStats = new AttackTraceService.AttackSourceStats();
        ipStats.setTotalAttacks(10);
        when(attackTraceService.getIpAttackStats(ipAddress)).thenReturn(ipStats);

        doNothing().when(hashOperations).putAll(anyString(), anyMap());
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        ActiveDefenseService.LockResult result =
                activeDefenseService.checkAndLockAccount(userId, ipAddress);

        assertTrue(result.isLocked());
        assertEquals("Attack threshold exceeded", result.getReason());
    }

    @Test
    @DisplayName("Check and lock account - IP attack threshold exceeded")
    void testCheckAndLockAccount_IpThresholdExceeded() {
        String userId = "user-ip-threshold";
        String ipAddress = "192.168.1.5";

        when(redisTemplate.hasKey(anyString())).thenReturn(false);

        AttackTraceService.UserAttackStats userStats = new AttackTraceService.UserAttackStats();
        userStats.setTotalAttacks(5);
        when(attackTraceService.getUserAttackStats(userId)).thenReturn(userStats);

        AttackTraceService.AttackSourceStats ipStats = new AttackTraceService.AttackSourceStats();
        ipStats.setTotalAttacks(60);
        when(attackTraceService.getIpAttackStats(ipAddress)).thenReturn(ipStats);

        doNothing().when(hashOperations).putAll(anyString(), anyMap());
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        ActiveDefenseService.LockResult result =
                activeDefenseService.checkAndLockAccount(userId, ipAddress);

        assertTrue(result.isLocked());
        assertEquals("IP attack threshold exceeded", result.getReason());
    }

    @Test
    @DisplayName("Lock account - stores lock data")
    void testLockAccount() {
        String userId = "user-to-lock";
        int durationSeconds = 1800;
        String reason = "Manual lock";

        doNothing().when(hashOperations).putAll(anyString(), anyMap());
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        assertDoesNotThrow(() ->
                activeDefenseService.lockAccount(userId, durationSeconds, reason));
    }

    @Test
    @DisplayName("Lock IP - stores lock data")
    void testLockIp() {
        String ipAddress = "192.168.1.100";
        int durationSeconds = 3600;
        String reason = "Manual lock";

        doNothing().when(hashOperations).putAll(anyString(), anyMap());
        when(redisTemplate.expire(anyString(), anyLong(), any())).thenReturn(true);

        assertDoesNotThrow(() ->
                activeDefenseService.lockIp(ipAddress, durationSeconds, reason));
    }

    @Test
    @DisplayName("Is account locked - returns true")
    void testIsAccountLocked_True() {
        String userId = "user-locked-check";

        when(redisTemplate.hasKey("replay:lock:account:" + userId)).thenReturn(true);

        assertTrue(activeDefenseService.isAccountLocked(userId));
    }

    @Test
    @DisplayName("Is account locked - returns false")
    void testIsAccountLocked_False() {
        String userId = "user-unlocked-check";

        when(redisTemplate.hasKey("replay:lock:account:" + userId)).thenReturn(false);

        assertFalse(activeDefenseService.isAccountLocked(userId));
    }

    @Test
    @DisplayName("Is IP locked - returns true")
    void testIsIpLocked_True() {
        String ipAddress = "192.168.1.101";

        when(redisTemplate.hasKey("replay:lock:ip:" + ipAddress)).thenReturn(true);

        assertTrue(activeDefenseService.isIpLocked(ipAddress));
    }

    @Test
    @DisplayName("Is IP locked - returns false")
    void testIsIpLocked_False() {
        String ipAddress = "192.168.1.102";

        when(redisTemplate.hasKey("replay:lock:ip:" + ipAddress)).thenReturn(false);

        assertFalse(activeDefenseService.isIpLocked(ipAddress));
    }

    @Test
    @DisplayName("Get account lock status - locked")
    void testGetAccountLockStatus_Locked() {
        String userId = "user-status-locked";

        when(redisTemplate.hasKey("replay:lock:account:" + userId)).thenReturn(true);

        Map<Object, Object> lockData = new HashMap<>();
        lockData.put("reason", "Test lock");
        lockData.put("lockTime", "1234567890");
        lockData.put("duration", "1800");

        when(hashOperations.entries("replay:lock:account:" + userId)).thenReturn(lockData);
        when(redisTemplate.getExpire("replay:lock:account:" + userId, java.util.concurrent.TimeUnit.SECONDS))
                .thenReturn(1500L);

        ActiveDefenseService.AccountLockStatus status =
                activeDefenseService.getAccountLockStatus(userId);

        assertTrue(status.isLocked());
        assertEquals("Test lock", status.getReason());
        assertEquals(1500L, status.getRemainingSeconds());
    }

    @Test
    @DisplayName("Get account lock status - not locked")
    void testGetAccountLockStatus_NotLocked() {
        String userId = "user-status-unlocked";

        when(redisTemplate.hasKey("replay:lock:account:" + userId)).thenReturn(false);

        ActiveDefenseService.AccountLockStatus status =
                activeDefenseService.getAccountLockStatus(userId);

        assertFalse(status.isLocked());
    }

    @Test
    @DisplayName("Unlock account - deletes lock key")
    void testUnlockAccount() {
        String userId = "user-to-unlock";

        doNothing().when(redisTemplate).delete("replay:lock:account:" + userId);

        assertDoesNotThrow(() -> activeDefenseService.unlockAccount(userId));

        verify(redisTemplate).delete("replay:lock:account:" + userId);
    }

    @Test
    @DisplayName("Unlock IP - deletes lock key")
    void testUnlockIp() {
        String ipAddress = "192.168.1.103";

        doNothing().when(redisTemplate).delete("replay:lock:ip:" + ipAddress);

        assertDoesNotThrow(() -> activeDefenseService.unlockIp(ipAddress));

        verify(redisTemplate).delete("replay:lock:ip:" + ipAddress);
    }

    @Test
    @DisplayName("Null handling - isAccountLocked returns false for null")
    void testIsAccountLocked_Null() {
        assertFalse(activeDefenseService.isAccountLocked(null));
        assertFalse(activeDefenseService.isAccountLocked(""));
    }

    @Test
    @DisplayName("Null handling - isIpLocked returns false for null")
    void testIsIpLocked_Null() {
        assertFalse(activeDefenseService.isIpLocked(null));
        assertFalse(activeDefenseService.isIpLocked(""));
    }
}
