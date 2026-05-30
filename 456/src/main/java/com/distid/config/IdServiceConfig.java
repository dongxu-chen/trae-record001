package com.distid.config;

import com.distid.ha.CrossDcSyncService;
import com.distid.ha.DatacenterRegistry;
import com.distid.ha.FailoverManager;
import com.distid.metrics.IdMetrics;
import com.distid.segment.SegmentIdService;
import com.distid.snowflake.NtpTimeSynchronizer;
import com.distid.snowflake.SnowflakeIdService;
import org.apache.curator.framework.CuratorFramework;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;

@Configuration
public class IdServiceConfig {

    @Value("${distid.snowflake.datacenter-id:0}")
    private long datacenterId;

    @Value("${distid.snowflake.max-tolerate-backward-ms:5}")
    private long maxTolerateBackwardMs;

    @Value("${distid.snowflake.max-wait-backward-ms:5000}")
    private long maxWaitBackwardMs;

    @Value("${distid.ntp.enabled:true}")
    private boolean ntpEnabled;

    @Value("${distid.ntp.sync-interval-minutes:5}")
    private int ntpSyncInterval;

    @Value("${distid.ntp.max-offset-ms:500}")
    private long ntpMaxOffsetMs;

    @Value("#{'${distid.ntp.servers:pool.ntp.org,time.windows.com,ntp.aliyun.com}'.split(',')}")
    private String[] ntpServers;

    @Value("${distid.ha.dc-code:dc1}")
    private String dcCode;

    @Value("${distid.ha.region:default}")
    private String region;

    @Value("${distid.ha.priority:1}")
    private int dcPriority;

    @Value("${distid.ha.segment-offset:0}")
    private long segmentOffset;

    @Value("${distid.ha.segment-step:1000}")
    private long segmentStep;

    @Bean
    public String podName() {
        String podName = System.getenv("POD_NAME");
        if (podName != null && !podName.isEmpty()) {
            return podName;
        }
        podName = System.getenv("HOSTNAME");
        if (podName != null && !podName.isEmpty()) {
            return podName;
        }
        try {
            return java.net.InetAddress.getLocalHost().getHostName();
        } catch (Exception e) {
            return "distid-pod-" + System.currentTimeMillis();
        }
    }

    @Bean
    @ConditionalOnProperty(name = "distid.ntp.enabled", havingValue = "true", matchIfMissing = true)
    public NtpTimeSynchronizer ntpTimeSynchronizer() {
        NtpTimeSynchronizer synchronizer = new NtpTimeSynchronizer(ntpServers, ntpSyncInterval, ntpMaxOffsetMs);
        synchronizer.start();
        return synchronizer;
    }

    @Bean
    public DatacenterRegistry datacenterRegistry(CuratorFramework curator) throws Exception {
        DatacenterRegistry registry = new DatacenterRegistry(curator, dcCode, region, dcPriority, segmentOffset, segmentStep);
        registry.init();
        return registry;
    }

    @Bean
    public CrossDcSyncService crossDcSyncService(StringRedisTemplate redisTemplate, DatacenterRegistry dcRegistry) {
        return new CrossDcSyncService(redisTemplate, dcRegistry);
    }

    @Bean
    public FailoverManager failoverManager(DatacenterRegistry dcRegistry, CrossDcSyncService crossDcSyncService,
                                            StringRedisTemplate redisTemplate) {
        return new FailoverManager(dcRegistry, crossDcSyncService, redisTemplate);
    }

    @Bean
    public SnowflakeIdService snowflakeIdService(CuratorFramework curator,
                                                  IdMetrics metrics,
                                                  String podName,
                                                  @Lazy NtpTimeSynchronizer ntpTimeSynchronizer) {
        NtpTimeSynchronizer actualSync = ntpEnabled ? ntpTimeSynchronizer : null;
        return new SnowflakeIdService(curator, datacenterId, maxTolerateBackwardMs,
                maxWaitBackwardMs, metrics, podName, actualSync);
    }

    @Bean
    public SegmentIdService segmentIdService(JdbcTemplate jdbcTemplate,
                                              StringRedisTemplate redisTemplate) {
        return new SegmentIdService(jdbcTemplate, redisTemplate);
    }
}
