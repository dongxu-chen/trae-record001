package com.distributed.lock.config;

import com.distributed.lock.analysis.AnalysisEventListener;
import com.distributed.lock.monitor.LockMonitorManager;
import com.distributed.lock.redis.RedisLockFactory;
import com.distributed.lock.zookeeper.ZkLockFactory;
import org.apache.curator.framework.CuratorFramework;
import org.apache.curator.framework.CuratorFrameworkFactory;
import org.apache.curator.retry.ExponentialBackoffRetry;
import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class LockConfig {

    @Value("${spring.application.name:lock-monitor}")
    private String applicationName;

    @Value("${redis.address:redis://localhost:6379}")
    private String redisAddress;

    @Value("${zookeeper.address:localhost:2181}")
    private String zookeeperAddress;

    @Bean
    public RedissonClient redissonClient() {
        Config config = new Config();
        config.useSingleServer()
                .setAddress(redisAddress)
                .setDatabase(0);
        return Redisson.create(config);
    }

    @Bean
    public CuratorFramework curatorFramework() {
        CuratorFramework curatorFramework = CuratorFrameworkFactory.newClient(
                zookeeperAddress,
                new ExponentialBackoffRetry(1000, 3)
        );
        curatorFramework.start();
        return curatorFramework;
    }

    @Bean
    public RedisLockFactory redisLockFactory(RedissonClient redissonClient) {
        return new RedisLockFactory(redissonClient, applicationName);
    }

    @Bean
    public ZkLockFactory zkLockFactory(CuratorFramework curatorFramework) {
        return new ZkLockFactory(curatorFramework, applicationName);
    }

    @Bean
    @Autowired
    public Void registerAnalysisListener(LockMonitorManager monitorManager, AnalysisEventListener analysisListener) {
        monitorManager.addListener(analysisListener);
        return null;
    }
}