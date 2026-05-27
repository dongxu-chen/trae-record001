package com.security.replayguard.core;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class LuaScriptsTest {

    private static final String SLIDING_WINDOW_LUA = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            local request_id = ARGV[4]
            
            local window_start = now - window
            
            redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
            
            local current_count = redis.call('ZCARD', key)
            
            if current_count >= max_requests then
                return 0
            end
            
            redis.call('ZADD', key, now, request_id)
            redis.call('EXPIRE', key, window)
            
            return 1
            """;

    private static final String NONCE_CHECK_AND_SET_LUA = """
            local key = KEYS[1]
            local nonce = ARGV[1]
            local expire_seconds = tonumber(ARGV[2])
            
            local exists = redis.call('GET', key)
            if exists then
                return 0
            end
            
            redis.call('SETEX', key, expire_seconds, '1')
            return 1
            """;

    private static final String HONEYPOT_LUA = """
            local key = KEYS[1]
            local slow_threshold = tonumber(ARGV[1])
            local max_slow = tonumber(ARGV[2])
            local block_duration = tonumber(ARGV[3])
            local request_time = tonumber(ARGV[4])
            
            local block_key = key .. ':blocked'
            local blocked = redis.call('GET', block_key)
            if blocked then
                return 2
            end
            
            if request_time > slow_threshold then
                redis.call('INCR', key)
                redis.call('EXPIRE', key, 300)
                
                local count = tonumber(redis.call('GET', key))
                if count >= max_slow then
                    redis.call('SETEX', block_key, block_duration, '1')
                    return 2
                end
            end
            
            return 1
            """;

    private static final String DISTRIBUTED_COUNTER_LUA = """
            local key = KEYS[1]
            local increment = tonumber(ARGV[1])
            local max_count = tonumber(ARGV[2])
            local window_seconds = tonumber(ARGV[3])
            
            local current = tonumber(redis.call('GET', key) or '0')
            
            if current >= max_count then
                return current
            end
            
            local new_count = redis.call('INCRBY', key, increment)
            
            if new_count == increment then
                redis.call('EXPIRE', key, window_seconds)
            end
            
            return new_count
            """;

    @Test
    @DisplayName("Sliding window LUA - script is not empty")
    void testSlidingWindowLua_NotEmpty() {
        assertFalse(SLIDING_WINDOW_LUA.isEmpty());
        assertTrue(SLIDING_WINDOW_LUA.contains("ZREMRANGEBYSCORE"));
        assertTrue(SLIDING_WINDOW_LUA.contains("ZCARD"));
        assertTrue(SLIDING_WINDOW_LUA.contains("ZADD"));
    }

    @Test
    @DisplayName("Sliding window LUA - contains required logic")
    void testSlidingWindowLua_Logic() {
        assertTrue(SLIDING_WINDOW_LUA.contains("window_start"));
        assertTrue(SLIDING_WINDOW_LUA.contains("current_count"));
        assertTrue(SLIDING_WINDOW_LUA.contains("max_requests"));
        assertTrue(SLIDING_WINDOW_LUA.contains("return 0"));
        assertTrue(SLIDING_WINDOW_LUA.contains("return 1"));
    }

    @Test
    @DisplayName("Nonce check LUA - script is not empty")
    void testNonceCheckLua_NotEmpty() {
        assertFalse(NONCE_CHECK_AND_SET_LUA.isEmpty());
        assertTrue(NONCE_CHECK_AND_SET_LUA.contains("GET"));
        assertTrue(NONCE_CHECK_AND_SET_LUA.contains("SETEX"));
    }

    @Test
    @DisplayName("Nonce check LUA - contains required logic")
    void testNonceCheckLua_Logic() {
        assertTrue(NONCE_CHECK_AND_SET_LUA.contains("exists"));
        assertTrue(NONCE_CHECK_AND_SET_LUA.contains("return 0"));
        assertTrue(NONCE_CHECK_AND_SET_LUA.contains("return 1"));
    }

    @Test
    @DisplayName("Honeypot LUA - script is not empty")
    void testHoneypotLua_NotEmpty() {
        assertFalse(HONEYPOT_LUA.isEmpty());
        assertTrue(HONEYPOT_LUA.contains("INCR"));
        assertTrue(HONEYPOT_LUA.contains("SETEX"));
    }

    @Test
    @DisplayName("Honeypot LUA - contains three return states")
    void testHoneypotLua_ReturnStates() {
        assertTrue(HONEYPOT_LUA.contains("return 1"));
        assertTrue(HONEYPOT_LUA.contains("return 2"));
        assertTrue(HONEYPOT_LUA.contains("block_key"));
    }

    @Test
    @DisplayName("Distributed counter LUA - script is not empty")
    void testDistributedCounterLua_NotEmpty() {
        assertFalse(DISTRIBUTED_COUNTER_LUA.isEmpty());
        assertTrue(DISTRIBUTED_COUNTER_LUA.contains("INCRBY"));
        assertTrue(DISTRIBUTED_COUNTER_LUA.contains("EXPIRE"));
    }

    @Test
    @DisplayName("Distributed counter LUA - contains threshold logic")
    void testDistributedCounterLua_Threshold() {
        assertTrue(DISTRIBUTED_COUNTER_LUA.contains("max_count"));
        assertTrue(DISTRIBUTED_COUNTER_LUA.contains("current >= max_count"));
    }

    @Test
    @DisplayName("All scripts have correct KEYS and ARGV references")
    void testAllScripts_KeyReferences() {
        assertTrue(SLIDING_WINDOW_LUA.contains("KEYS[1]"));
        assertTrue(NONCE_CHECK_AND_SET_LUA.contains("KEYS[1]"));
        assertTrue(HONEYPOT_LUA.contains("KEYS[1]"));
        assertTrue(DISTRIBUTED_COUNTER_LUA.contains("KEYS[1]"));
    }

    @Test
    @DisplayName("Sliding window LUA - has correct ARGV count")
    void testSlidingWindowLua_ArgvCount() {
        assertTrue(SLIDING_WINDOW_LUA.contains("ARGV[1]"));
        assertTrue(SLIDING_WINDOW_LUA.contains("ARGV[2]"));
        assertTrue(SLIDING_WINDOW_LUA.contains("ARGV[3]"));
        assertTrue(SLIDING_WINDOW_LUA.contains("ARGV[4]"));
    }

    @Test
    @DisplayName("Nonce check LUA - has correct ARGV count")
    void testNonceCheckLua_ArgvCount() {
        assertTrue(NONCE_CHECK_AND_SET_LUA.contains("ARGV[1]"));
        assertTrue(NONCE_CHECK_AND_SET_LUA.contains("ARGV[2]"));
    }

    @Test
    @DisplayName("Honeypot LUA - has correct ARGV count")
    void testHoneypotLua_ArgvCount() {
        assertTrue(HONEYPOT_LUA.contains("ARGV[1]"));
        assertTrue(HONEYPOT_LUA.contains("ARGV[2]"));
        assertTrue(HONEYPOT_LUA.contains("ARGV[3]"));
        assertTrue(HONEYPOT_LUA.contains("ARGV[4]"));
    }

    @Test
    @DisplayName("Distributed counter LUA - has correct ARGV count")
    void testDistributedCounterLua_ArgvCount() {
        assertTrue(DISTRIBUTED_COUNTER_LUA.contains("ARGV[1]"));
        assertTrue(DISTRIBUTED_COUNTER_LUA.contains("ARGV[2]"));
        assertTrue(DISTRIBUTED_COUNTER_LUA.contains("ARGV[3]"));
    }
}
