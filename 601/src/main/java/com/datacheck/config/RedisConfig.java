package com.datacheck.config;

import io.lettuce.core.ClientOptions;
import io.lettuce.core.SocketOptions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

@Configuration
public class RedisConfig {

    @Value("${data.redis.source.host:localhost}")
    private String sourceHost;

    @Value("${data.redis.source.port:6379}")
    private int sourcePort;

    @Value("${data.redis.source.password:}")
    private String sourcePassword;

    @Value("${data.redis.source.database:0}")
    private int sourceDatabase;

    @Value("${data.redis.source.timeout:3000}")
    private long sourceTimeout;

    @Value("${data.redis.target.host:localhost}")
    private String targetHost;

    @Value("${data.redis.target.port:6380}")
    private int targetPort;

    @Value("${data.redis.target.password:}")
    private String targetPassword;

    @Value("${data.redis.target.database:0}")
    private int targetDatabase;

    @Value("${data.redis.target.timeout:3000}")
    private long targetTimeout;

    @Bean(name = "sourceRedisConnectionFactory")
    public RedisConnectionFactory sourceRedisConnectionFactory() {
        return createConnectionFactory(sourceHost, sourcePort, sourcePassword, sourceDatabase, sourceTimeout);
    }

    @Bean(name = "targetRedisConnectionFactory")
    public RedisConnectionFactory targetRedisConnectionFactory() {
        return createConnectionFactory(targetHost, targetPort, targetPassword, targetDatabase, targetTimeout);
    }

    @Bean(name = "sourceRedisTemplate")
    public RedisTemplate<String, Object> sourceRedisTemplate(
            @org.springframework.beans.factory.annotation.Qualifier("sourceRedisConnectionFactory")
            RedisConnectionFactory connectionFactory) {
        return createRedisTemplate(connectionFactory);
    }

    @Bean(name = "targetRedisTemplate")
    public RedisTemplate<String, Object> targetRedisTemplate(
            @org.springframework.beans.factory.annotation.Qualifier("targetRedisConnectionFactory")
            RedisConnectionFactory connectionFactory) {
        return createRedisTemplate(connectionFactory);
    }

    @Bean(name = "sourceStringRedisTemplate")
    public StringRedisTemplate sourceStringRedisTemplate(
            @org.springframework.beans.factory.annotation.Qualifier("sourceRedisConnectionFactory")
            RedisConnectionFactory connectionFactory) {
        return new StringRedisTemplate(connectionFactory);
    }

    @Bean(name = "targetStringRedisTemplate")
    public StringRedisTemplate targetStringRedisTemplate(
            @org.springframework.beans.factory.annotation.Qualifier("targetRedisConnectionFactory")
            RedisConnectionFactory connectionFactory) {
        return new StringRedisTemplate(connectionFactory);
    }

    private RedisConnectionFactory createConnectionFactory(String host, int port, String password,
                                                           int database, long timeout) {
        RedisStandaloneConfiguration config = new RedisStandaloneConfiguration();
        config.setHostName(host);
        config.setPort(port);
        if (password != null && !password.isEmpty()) {
            config.setPassword(password);
        }
        config.setDatabase(database);

        LettuceClientConfiguration clientConfig = LettuceClientConfiguration.builder()
                .clientOptions(ClientOptions.builder()
                        .socketOptions(SocketOptions.builder()
                                .connectTimeout(Duration.ofMillis(timeout))
                                .build())
                        .build())
                .commandTimeout(Duration.ofMillis(timeout))
                .build();

        return new LettuceConnectionFactory(config, clientConfig);
    }

    private RedisTemplate<String, Object> createRedisTemplate(RedisConnectionFactory connectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.afterPropertiesSet();
        return template;
    }
}
