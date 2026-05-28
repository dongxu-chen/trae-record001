package com.configcenter.client.listener;

import com.configcenter.client.config.AppConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.context.scope.refresh.RefreshScopeRefreshedEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class ConfigRefreshListener {

    private static final Logger logger = LoggerFactory.getLogger(ConfigRefreshListener.class);

    @Autowired
    private AppConfig appConfig;

    @EventListener
    public void onRefresh(RefreshScopeRefreshedEvent event) {
        logger.info("========================================");
        logger.info("配置刷新事件已触发，最新配置如下:");
        logger.info("功能开关 - enabled: {}", appConfig.getFeature().isEnabled());
        logger.info("阈值配置 - maxRequests: {}", appConfig.getThreshold().getMaxRequests());
        logger.info("阈值配置 - timeoutMs: {}", appConfig.getThreshold().getTimeoutMs());
        logger.info("数据库配置 - maxConnections: {}", appConfig.getDatabase().getMaxConnections());
        logger.info("数据库配置 - minIdle: {}", appConfig.getDatabase().getMinIdle());
        logger.info("========================================");
    }
}
