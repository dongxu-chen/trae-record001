package com.gateway.plugin;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class PluginManager {

    private final ApplicationContext applicationContext;
    private List<GatewayPlugin> sortedPlugins;

    @PostConstruct
    public void init() {
        Map<String, GatewayPlugin> pluginBeans = applicationContext.getBeansOfType(GatewayPlugin.class);
        sortedPlugins = new ArrayList<>(pluginBeans.values());
        sortedPlugins.sort(Comparator.comparingInt(GatewayPlugin::getOrder));

        log.info("Loaded {} gateway plugins:", sortedPlugins.size());
        sortedPlugins.forEach(plugin -> log.info("  - {} (order: {}, enabled: {})",
                plugin.getName(), plugin.getOrder(), plugin.isEnabled()));
    }

    public List<GatewayPlugin> getPlugins() {
        return sortedPlugins;
    }

    public PluginChain createChain(Runnable onComplete) {
        return new DefaultPluginChain(new ArrayList<>(sortedPlugins), onComplete);
    }
}
