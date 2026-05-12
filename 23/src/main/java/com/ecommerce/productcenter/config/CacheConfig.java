package com.ecommerce.productcenter.config;

import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(10))
                .serializeKeysWith(RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer()))
                .computePrefixWith(cacheName -> "product-center:" + cacheName + ":");

        Map<String, RedisCacheConfiguration> cacheConfigurations = new HashMap<>();

        cacheConfigurations.put("product", defaultConfig.entryTtl(Duration.ofMinutes(30)));
        cacheConfigurations.put("products", defaultConfig.entryTtl(Duration.ofMinutes(5)));
        cacheConfigurations.put("productsByCategory", defaultConfig.entryTtl(Duration.ofMinutes(10)));
        cacheConfigurations.put("productsSearch", defaultConfig.entryTtl(Duration.ofMinutes(2)));
        
        cacheConfigurations.put("sku", defaultConfig.entryTtl(Duration.ofMinutes(30)));
        cacheConfigurations.put("skus", defaultConfig.entryTtl(Duration.ofMinutes(5)));
        cacheConfigurations.put("skusByProduct", defaultConfig.entryTtl(Duration.ofMinutes(10)));

        return RedisCacheManager.builder(connectionFactory)
                .cacheDefaults(defaultConfig)
                .withInitialCacheConfigurations(cacheConfigurations)
                .build();
    }
}
