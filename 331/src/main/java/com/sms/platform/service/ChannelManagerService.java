package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sms.platform.common.exception.BusinessException;
import com.sms.platform.entity.SmsChannelConfig;
import com.sms.platform.mapper.SmsChannelConfigMapper;
import com.sms.platform.sdk.SmsProvider;
import com.sms.platform.sdk.SmsProviderFactory;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

@Slf4j
@Service
public class ChannelManagerService {

    @Resource
    private SmsChannelConfigMapper channelConfigMapper;

    @Value("${sms.channel.fail-threshold:3}")
    private int failThreshold;

    private final Map<Integer, SmsChannelConfig> channelConfigCache = new ConcurrentHashMap<>();
    private final Map<Integer, AtomicInteger> failCountMap = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        refreshChannelCache();
        log.info("通道管理器初始化完成, 共加载 {} 个通道配置", channelConfigCache.size());
    }

    public void refreshChannelCache() {
        List<SmsChannelConfig> configs = channelConfigMapper.selectList(
                new LambdaQueryWrapper<SmsChannelConfig>()
                        .eq(SmsChannelConfig::getStatus, 1)
                        .eq(SmsChannelConfig::getDeleted, 0)
        );
        for (SmsChannelConfig config : configs) {
            channelConfigCache.put(config.getChannelCode(), config);
            failCountMap.put(config.getChannelCode(), new AtomicInteger(0));
        }
    }

    public SmsChannelConfig selectChannel() {
        List<SmsChannelConfig> healthyChannels = getHealthyChannels();
        healthyChannels.sort((c1, c2) -> {
            if (c1.getIsMaster().equals(c2.getIsMaster())) {
                return c2.getWeight() - c1.getWeight();
            }
            return c2.getIsMaster() - c1.getIsMaster();
        });

        if (!healthyChannels.isEmpty()) {
            return healthyChannels.get(0);
        }

        log.warn("无健康通道可用，尝试使用非健康主通道");
        for (SmsChannelConfig config : channelConfigCache.values()) {
            if (config.getIsMaster() == 1) {
                return config;
            }
        }

        throw new BusinessException("无可用短信通道");
    }

    public SmsChannelConfig selectChannelByType(Integer smsType) {
        return selectChannel();
    }

    public List<SmsChannelConfig> getHealthyChannels() {
        List<SmsChannelConfig> result = new ArrayList<>();
        for (SmsChannelConfig config : channelConfigCache.values()) {
            if (config.getStatus() == 1 && config.getIsHealthy() == 1) {
                SmsProvider provider = SmsProviderFactory.getProvider(config.getChannelCode());
                if (provider != null) {
                    result.add(config);
                }
            }
        }
        return result;
    }

    public SmsChannelConfig getChannelConfig(Integer channelCode) {
        return channelConfigCache.get(channelCode);
    }

    public void recordSuccess(Integer channelCode) {
        AtomicInteger counter = failCountMap.get(channelCode);
        if (counter != null) {
            counter.set(0);
        }
        SmsChannelConfig config = channelConfigCache.get(channelCode);
        if (config != null && config.getIsHealthy() == 0) {
            config.setIsHealthy(1);
            config.setFailCount(0);
            channelConfigMapper.updateById(config);
            log.info("通道 {} 恢复健康", channelCode);
        }
    }

    public void recordFail(Integer channelCode) {
        AtomicInteger counter = failCountMap.get(channelCode);
        if (counter != null) {
            int currentFail = counter.incrementAndGet();
            log.warn("通道 {} 连续失败次数: {}", channelCode, currentFail);

            if (currentFail >= failThreshold) {
                markChannelUnhealthy(channelCode);
            }
        }
    }

    private void markChannelUnhealthy(Integer channelCode) {
        SmsChannelConfig config = channelConfigCache.get(channelCode);
        if (config != null && config.getIsHealthy() == 1) {
            config.setIsHealthy(0);
            config.setFailCount(failCountMap.get(channelCode).get());
            channelConfigMapper.updateById(config);
            log.error("通道 {} 连续失败超过阈值 {}，标记为不健康", channelCode, failThreshold);

            trySwitchToBackup(channelCode);
        }
    }

    private void trySwitchToBackup(Integer failedChannelCode) {
        SmsChannelConfig failedConfig = channelConfigCache.get(failedChannelCode);
        if (failedConfig != null && failedConfig.getIsMaster() == 1) {
            for (SmsChannelConfig config : channelConfigCache.values()) {
                if (!config.getChannelCode().equals(failedChannelCode)
                        && config.getIsHealthy() == 1
                        && config.getStatus() == 1) {
                    log.info("主通道 {} 故障，切换到备用通道 {}", failedChannelCode, config.getChannelCode());
                    break;
                }
            }
        }
    }

    @Scheduled(fixedDelayString = "${sms.channel.health-check-interval:60000}")
    public void healthCheckTask() {
        log.debug("开始执行通道健康检查任务");
        for (Map.Entry<Integer, SmsChannelConfig> entry : channelConfigCache.entrySet()) {
            Integer channelCode = entry.getKey();
            SmsChannelConfig config = entry.getValue();

            SmsProvider provider = SmsProviderFactory.getProvider(channelCode);
            if (provider == null) {
                continue;
            }

            try {
                boolean healthy = provider.healthCheck();
                if (healthy && config.getIsHealthy() == 0) {
                    config.setIsHealthy(1);
                    config.setFailCount(0);
                    failCountMap.get(channelCode).set(0);
                    channelConfigMapper.updateById(config);
                    log.info("通道 {} 健康检查通过，恢复为健康状态", channelCode);
                } else if (!healthy && config.getIsHealthy() == 1) {
                    log.warn("通道 {} 健康检查失败", channelCode);
                }
            } catch (Exception e) {
                log.error("通道 {} 健康检查异常", channelCode, e);
            }
        }
    }

    public List<SmsChannelConfig> getAllChannelConfigs() {
        return new ArrayList<>(channelConfigCache.values());
    }

    public void updateChannelConfig(SmsChannelConfig config) {
        if (config == null || config.getChannelCode() == null) {
            return;
        }
        channelConfigMapper.updateById(config);
        channelConfigCache.put(config.getChannelCode(), config);
        log.info("通道配置已更新, channelCode={}, isHealthy={}", config.getChannelCode(), config.getIsHealthy());
    }
}
