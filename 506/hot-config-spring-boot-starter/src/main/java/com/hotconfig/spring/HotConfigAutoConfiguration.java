package com.hotconfig.spring;

import com.hotconfig.annotation.EnableHotConfig;
import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.health.ConfigHealthChecker;
import com.hotconfig.core.health.ConfigHealthCheckResult;
import com.hotconfig.core.listener.ConfigListenerMethodProcessor;
import com.hotconfig.core.proxy.DynamicProxyFactory;
import com.hotconfig.core.refresh.BeanPropertyRefresher;
import com.hotconfig.core.source.ApolloConfigSource;
import com.hotconfig.core.source.FileConfigSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.ApplicationListener;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.event.ContextRefreshedEvent;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

@Configuration
@EnableConfigurationProperties(HotConfigProperties.class)
@ConditionalOnProperty(prefix = "hotconfig", name = "enabled", havingValue = "true", matchIfMissing = true)
public class HotConfigAutoConfiguration implements ApplicationListener<ContextRefreshedEvent> {

    private static final Logger logger = LoggerFactory.getLogger(HotConfigAutoConfiguration.class);

    private final HotConfigProperties properties;

    private BeanPropertyRefresher propertyRefresher;
    private ConfigHealthChecker healthChecker;

    private volatile boolean contextRefreshed = false;

    public HotConfigAutoConfiguration(HotConfigProperties properties) {
        this.properties = properties;
    }

    @PostConstruct
    public void init() {
        logger.info("Initializing Hot Config Auto Configuration...");

        ConfigManager configManager = ConfigManager.getInstance();
        if (!configManager.isInitialized()) {
            configManager.init();
        }

        configureConfigSources(configManager);

        configManager.setRollbackEnabled(properties.isRollbackEnabled());
        configManager.setDiffNotificationEnabled(properties.isDiffNotificationEnabled());

        logger.info("Hot Config Auto Configuration initialized successfully");
    }

    @Override
    public void onApplicationEvent(ContextRefreshedEvent event) {
        if (contextRefreshed) {
            return;
        }
        contextRefreshed = true;

        logger.info("Context refreshed, flushing deferred config refreshes...");

        if (propertyRefresher != null) {
            propertyRefresher.setDeferMode(false);
        }

        logger.info("Deferred config refreshes completed");

        if (properties.isHealthCheckEnabled() && healthChecker != null) {
            performHealthCheck();
        }

        if (properties.isScheduledHealthCheckEnabled()) {
            healthChecker.startScheduledCheck(properties.getHealthCheckIntervalMs());
            logger.info("Scheduled health check started with interval: {}ms", properties.getHealthCheckIntervalMs());
        }
    }

    private void performHealthCheck() {
        try {
            logger.info("Performing initial configuration health check...");
            ConfigHealthCheckResult result = healthChecker.performFullCheck();
            logger.info("Health check completed with status: {}, {} issues found",
                    result.getOverallStatus(), result.getIssueCount());

            if (!result.isHealthy()) {
                logger.warn("Configuration health check found issues:\n{}", result.getSummary());

                if (properties.isFailOnHealthCheckWarning() && result.getOverallStatus() == ConfigHealthCheckResult.HealthStatus.WARNING) {
                    logger.warn("Health check returned WARNING status (failOnHealthCheckWarning=true)");
                }

                if (properties.isFailOnHealthCheckError() && result.hasCriticalIssues()) {
                    logger.error("Health check returned CRITICAL status, but application will continue running");
                }
            } else {
                logger.info("Configuration health check passed - all checks are healthy");
            }
        } catch (Exception e) {
            logger.error("Failed to perform health check", e);
        }
    }

    private void configureConfigSources(ConfigManager configManager) {
        for (String fileSource : properties.getFileSources()) {
            try {
                FileConfigSource configSource = new FileConfigSource(fileSource, properties.isEnableFileWatch());
                configManager.addConfigSource(configSource);
                logger.info("Added file config source: {}", fileSource);
            } catch (Exception e) {
                logger.error("Failed to add file config source: {}", fileSource, e);
            }
        }

        if (properties.isEnableApollo() && ApolloConfigSource.isApolloAvailable()) {
            try {
                if (properties.getApolloAppId() != null) {
                    System.setProperty("app.id", properties.getApolloAppId());
                }
                if (properties.getApolloMetaServer() != null) {
                    System.setProperty("apollo.meta", properties.getApolloMetaServer());
                }

                if (properties.getApolloNamespaces().isEmpty()) {
                    ApolloConfigSource apolloSource = new ApolloConfigSource();
                    configManager.addConfigSource(apolloSource);
                    logger.info("Added Apollo config source for default namespace");
                } else {
                    for (String namespace : properties.getApolloNamespaces()) {
                        ApolloConfigSource apolloSource = new ApolloConfigSource(namespace);
                        configManager.addConfigSource(apolloSource);
                        logger.info("Added Apollo config source for namespace: {}", namespace);
                    }
                }
            } catch (Exception e) {
                logger.error("Failed to add Apollo config source", e);
            }
        }
    }

    @Bean
    @ConditionalOnMissingBean
    public ConfigManager configManager() {
        ConfigManager configManager = ConfigManager.getInstance();
        if (!configManager.isInitialized()) {
            configManager.init();
        }
        return configManager;
    }

    @Bean
    @ConditionalOnMissingBean
    public DynamicProxyFactory dynamicProxyFactory() {
        return DynamicProxyFactory.getInstance();
    }

    @Bean
    @ConditionalOnMissingBean
    public BeanPropertyRefresher beanPropertyRefresher(ConfigManager configManager,
                                                        DynamicProxyFactory proxyFactory) {
        BeanPropertyRefresher refresher = new BeanPropertyRefresher(configManager, proxyFactory);
        refresher.setDeferMode(true);
        this.propertyRefresher = refresher;
        logger.info("BeanPropertyRefresher created with deferMode enabled");
        return refresher;
    }

    @Bean
    @ConditionalOnMissingBean
    public ConfigListenerMethodProcessor configListenerMethodProcessor(ConfigManager configManager) {
        return new ConfigListenerMethodProcessor(configManager);
    }

    @Bean
    @ConditionalOnMissingBean
    public ConfigHealthChecker configHealthChecker(ConfigManager configManager) {
        ConfigHealthChecker checker = ConfigHealthChecker.getInstance(configManager);
        this.healthChecker = checker;
        logger.info("ConfigHealthChecker created");
        return checker;
    }

    @Bean
    @ConditionalOnMissingBean
    public HotConfigBeanPostProcessor hotConfigBeanPostProcessor(ConfigManager configManager,
                                                                   DynamicProxyFactory proxyFactory,
                                                                   BeanPropertyRefresher propertyRefresher,
                                                                   ConfigListenerMethodProcessor listenerProcessor) {
        return new HotConfigBeanPostProcessor(configManager, proxyFactory, propertyRefresher, listenerProcessor);
    }

    @PreDestroy
    public void destroy() {
        logger.info("Destroying Hot Config Auto Configuration...");
        ConfigManager.getInstance().destroy();
        logger.info("Hot Config Auto Configuration destroyed");
    }

    @Configuration
    @ConditionalOnClass(EnableHotConfig.class)
    public static class EnableHotConfigConfiguration {
    }
}
