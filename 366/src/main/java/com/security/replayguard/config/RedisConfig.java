package com.security.replayguard.config;

import io.lettuce.core.ClientOptions;
import io.lettuce.core.SocketOptions;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;

import java.time.Duration;

@Configuration
public class RedisConfig {

    @Bean
    public LettuceConnectionFactory redisConnectionFactory() {
        RedisStandaloneConfiguration config = new RedisStandaloneConfiguration();
        config.setHostName("127.0.0.1");
        config.setPort(6379);

        SocketOptions socketOptions = SocketOptions.builder()
                .connectTimeout(Duration.ofSeconds(5))
                .keepAlive(true)
                .build();

        ClientOptions clientOptions = ClientOptions.builder()
                .socketOptions(socketOptions)
                .autoReconnect(true)
                .build();

        LettuceClientConfiguration clientConfig = LettuceClientConfiguration.builder()
                .clientOptions(clientOptions)
                .commandTimeout(Duration.ofSeconds(5))
                .shutdownTimeout(Duration.ofSeconds(2))
                .build();

        return new LettuceConnectionFactory(config, clientConfig);
    }

    @Bean
    public StringRedisTemplate stringRedisTemplate(RedisConnectionFactory connectionFactory) {
        StringRedisTemplate template = new StringRedisTemplate();
        template.setConnectionFactory(connectionFactory);
        template.setEnableTransactionSupport(true);
        return template;
    }

    @Bean
    public RedisScript<Long> slidingWindowScript() {
        DefaultRedisScript<Long> script = new DefaultRedisScript<>();
        script.setScriptSource(new org.springframework.scripting.support.StaticScriptSource(
                SLIDING_WINDOW_LUA
        ));
        script.setResultType(Long.class);
        return script;
    }

    @Bean
    public RedisScript<Long> nonceCheckAndSetScript() {
        DefaultRedisScript<Long> script = new DefaultRedisScript<>();
        script.setScriptSource(new org.springframework.scripting.support.StaticScriptSource(
                NONCE_CHECK_AND_SET_LUA
        ));
        script.setResultType(Long.class);
        return script;
    }

    @Bean
    public RedisScript<Long> honeypotScript() {
        DefaultRedisScript<Long> script = new DefaultRedisScript<>();
        script.setScriptSource(new org.springframework.scripting.support.StaticScriptSource(
                HONEYPOT_LUA
        ));
        script.setResultType(Long.class);
        return script;
    }

    @Bean
    public RedisScript<Long> distributedCounterScript() {
        DefaultRedisScript<Long> script = new DefaultRedisScript<>();
        script.setScriptSource(new org.springframework.scripting.support.StaticScriptSource(
                DISTRIBUTED_COUNTER_LUA
        ));
        script.setResultType(Long.class);
        return script;
    }

    @Bean
    public RedisScript<Long> dualBufferSlidingWindowScript() {
        DefaultRedisScript<Long> script = new DefaultRedisScript<>();
        script.setScriptSource(new org.springframework.scripting.support.StaticScriptSource(
                DUAL_BUFFER_SLIDING_WINDOW_LUA
        ));
        script.setResultType(Long.class);
        return script;
    }

    @Bean
    public RedisScript<Long> dynamicHoneypotScript() {
        DefaultRedisScript<Long> script = new DefaultRedisScript<>();
        script.setScriptSource(new org.springframework.scripting.support.StaticScriptSource(
                DYNAMIC_HONEYPOT_LUA
        ));
        script.setResultType(Long.class);
        return script;
    }

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

    private static final String DUAL_BUFFER_SLIDING_WINDOW_LUA = """
            local current_key = KEYS[1]
            local previous_key = KEYS[2]
            local meta_key = KEYS[3]
            local now = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local max_requests = tonumber(ARGV[3])
            local request_id = ARGV[4]
            local overlap_seconds = tonumber(ARGV[5])
            local dual_buffer_enabled = tonumber(ARGV[6])
            local write_both = tonumber(ARGV[7])

            local window_start = now - window

            redis.call('ZREMRANGEBYSCORE', current_key, '-inf', window_start)
            redis.call('ZREMRANGEBYSCORE', previous_key, '-inf', window_start)

            if dual_buffer_enabled == 1 then
                local last_switch_str = redis.call('GET', meta_key)
                local last_switch = last_switch_str and tonumber(last_switch_str) or now
                local in_overlap = (now - last_switch) <= overlap_seconds
                local needs_switch = (now - last_switch) >= window

                if needs_switch then
                    redis.call('RENAME', current_key, previous_key)
                    redis.call('SETEX', meta_key, window * 2, tostring(now))
                    in_overlap = true
                end

                local current_count = redis.call('ZCARD', current_key)
                local previous_overlap_count = redis.call('ZCOUNT', previous_key, now - overlap_seconds, now)
                local total_count = current_count + (previous_overlap_count and previous_overlap_count or 0)

                if total_count >= max_requests then
                    return 0
                end

                redis.call('ZADD', current_key, now, request_id)
                redis.call('EXPIRE', current_key, window)

                if in_overlap and write_both == 1 then
                    redis.call('ZADD', previous_key, now, request_id)
                    redis.call('EXPIRE', previous_key, window + overlap_seconds)
                end

                return 1
            else
                local current_count = redis.call('ZCARD', current_key)

                if current_count >= max_requests then
                    return 0
                end

                redis.call('ZADD', current_key, now, request_id)
                redis.call('EXPIRE', current_key, window)

                return 1
            end
            """;

    private static final String DYNAMIC_HONEYPOT_LUA = """
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
}
