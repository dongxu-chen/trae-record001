package com.configcenter.spring;

import com.configcenter.client.ConfigChangeEvent;
import com.configcenter.client.ConfigChangeListener;
import com.configcenter.client.ConfigServiceClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationListener;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.event.ContextClosedEvent;
import org.springframework.context.event.ContextRefreshedEvent;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.Environment;
import org.springframework.core.env.MapPropertySource;

import javax.annotation.PostConstruct;
import java.util.HashMap;
import java.util.Map;

/**
 * 配置中心自动配置
 */
@Configuration
@EnableConfigurationProperties(ConfigCenterProperties.class)
@ConditionalOnProperty(prefix = "config.center", name = "enabled", havingValue = "true", matchIfMissing = true)
public class ConfigCenterAutoConfiguration {

    private static final Logger log = LoggerFactory.getLogger(ConfigCenterAutoConfiguration.class);
    private static final String PROPERTY_SOURCE_NAME = "configCenterPropertySource";

    @Autowired
    private ConfigCenterProperties properties;

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private Environment environment;

    private ConfigServiceClient configClient;

    @Bean
    @ConditionalOnMissingBean
    public ConfigServiceClient configServiceClient() {
        configClient = ConfigServiceClient.builder()
                .serverHost(properties.getServerHost())
                .serverPort(properties.getServerPort())
                .clientId(properties.getClientId())
                .serviceName(properties.getServiceName())
                .namespace(properties.getNamespace())
                .group(properties.getGroup())
                .build();

        log.info("ConfigServiceClient 创建完成, server: {}:{}, serviceName: {}",
                properties.getServerHost(), properties.getServerPort(), properties.getServiceName());

        return configClient;
    }

    @Bean
    public ConfigCenterLifecycleListener configCenterLifecycleListener() {
        return new ConfigCenterLifecycleListener(configServiceClient(), properties, environment);
    }

    /**
     * 生命周期监听器
     */
    public static class ConfigCenterLifecycleListener implements ApplicationListener<ContextRefreshedEvent> {

        private final ConfigServiceClient configClient;
        private final ConfigCenterProperties properties;
        private final Environment environment;
        private boolean initialized = false;

        public ConfigCenterLifecycleListener(ConfigServiceClient configClient,
                                              ConfigCenterProperties properties,
                                              Environment environment) {
            this.configClient = configClient;
            this.properties = properties;
            this.environment = environment;
        }

        @Override
        public void onApplicationEvent(ContextRefreshedEvent event) {
            if (!initialized) {
                initialize();
                initialized = true;
            }
        }

        private void initialize() {
            try {
                if (properties.isAutoStartup()) {
                    // 启动客户端
                    configClient.start();

                    // 订阅配置
                    if (properties.getSubscribeDataIds() != null && properties.getSubscribeDataIds().length > 0) {
                        configClient.subscribe(properties.getSubscribeDataIds());
                    }

                    // 添加配置变更监听器，同步到Spring Environment
                    configClient.addChangeListener(new SpringEnvironmentSyncListener(
                            (ConfigurableEnvironment) environment));

                    log.info("配置中心客户端初始化完成, 订阅配置: {}",
                            String.join(",", properties.getSubscribeDataIds()));
                }
            } catch (Exception e) {
                log.error("配置中心客户端初始化失败", e);
            }
        }
    }

    /**
     * Spring Environment同步监听器
     */
    public static class SpringEnvironmentSyncListener implements ConfigChangeListener {

        private final ConfigurableEnvironment environment;

        public SpringEnvironmentSyncListener(ConfigurableEnvironment environment) {
            this.environment = environment;
        }

        @Override
        public void onChange(ConfigChangeEvent event) {
            try {
                // 获取或创建PropertySource
                MapPropertySource propertySource;
                if (environment.getPropertySources().contains(PROPERTY_SOURCE_NAME)) {
                    propertySource = (MapPropertySource) environment.getPropertySources().get(PROPERTY_SOURCE_NAME);
                    // 更新PropertySource
                    Map<String, Object> source = new HashMap<>(propertySource.getSource());
                    for (ConfigChangeEvent.ChangeItem change : event.getChanges()) {
                        switch (change.getChangeType()) {
                            case ADDED:
                            case MODIFIED:
                                source.put(change.getKey(), change.getNewValue());
                                break;
                            case DELETED:
                                source.remove(change.getKey());
                                break;
                        }
                    }
                    environment.getPropertySources().remove(PROPERTY_SOURCE_NAME);
                    environment.getPropertySources().addFirst(new MapPropertySource(PROPERTY_SOURCE_NAME, source));
                } else {
                    // 首次创建
                    Map<String, Object> source = new HashMap<>();
                    for (ConfigChangeEvent.ChangeItem change : event.getChanges()) {
                        if (change.getChangeType() != ConfigChangeEvent.ChangeType.DELETED) {
                            source.put(change.getKey(), change.getNewValue());
                        }
                    }
                    environment.getPropertySources().addFirst(new MapPropertySource(PROPERTY_SOURCE_NAME, source));
                }

                log.info("配置变更已同步到Spring Environment, 变更数: {}", event.getChangeCount());

            } catch (Exception e) {
                log.error("同步配置变更到Spring Environment失败", e);
            }
        }
    }

    /**
     * 关闭时清理资源
     */
    @Bean
    public ApplicationListener<ContextClosedEvent> contextClosedListener() {
        return event -> {
            if (configClient != null) {
                try {
                    configClient.close();
                    log.info("配置中心客户端已关闭");
                } catch (Exception e) {
                    log.warn("关闭配置中心客户端异常", e);
                }
            }
        };
    }

    /**
     * 配置值注解处理器
     */
    @PostConstruct
    public void init() {
        log.info("配置中心自动配置已启用");
    }
}
