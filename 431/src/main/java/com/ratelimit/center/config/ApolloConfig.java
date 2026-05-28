package com.ratelimit.center.config;

import com.ctrip.framework.apollo.Config;
import com.ctrip.framework.apollo.ConfigService;
import com.ctrip.framework.apollo.model.ConfigChangeEvent;
import com.ctrip.framework.apollo.spring.annotation.ApolloConfig;
import com.ctrip.framework.apollo.spring.annotation.ApolloConfigChangeListener;
import com.ctrip.framework.apollo.spring.annotation.EnableApolloConfig;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;

import javax.annotation.PostConstruct;
import java.util.Set;

@Slf4j
@Configuration
@ConditionalOnProperty(name = "rate-limit.apollo.enabled", havingValue = "true")
@EnableApolloConfig
public class ApolloConfig {

    @ApolloConfig
    private Config config;

    @Value("${rate-limit.apollo.namespace:application}")
    private String namespace;

    @Autowired
    private com.ratelimit.center.service.FlowRuleService flowRuleService;

    @Autowired
    private com.ratelimit.center.service.DegradeRuleService degradeRuleService;

    @Autowired
    private com.ratelimit.center.service.ParamFlowRuleService paramFlowRuleService;

    @Autowired
    private com.ratelimit.center.service.SystemRuleService systemRuleService;

    @PostConstruct
    public void init() {
        log.info("Apollo config initialized, namespace: {}", namespace);
        syncRulesFromApollo();
    }

    @ApolloConfigChangeListener(interestedKeyPrefixes = {"sentinel.flow.", "sentinel.degrade.", "sentinel.param.", "sentinel.system."})
    public void onChange(ConfigChangeEvent changeEvent) {
        log.info("Apollo config changed, changed keys: {}", changeEvent.changedKeys());
        syncRulesFromApollo();
    }

    private void syncRulesFromApollo() {
        try {
            Set<String> propertyNames = config.getPropertyNames();
            log.info("Syncing rules from Apollo, total properties: {}", propertyNames.size());

            boolean hasFlowRuleChange = propertyNames.stream().anyMatch(k -> k.startsWith("sentinel.flow."));
            boolean hasDegradeRuleChange = propertyNames.stream().anyMatch(k -> k.startsWith("sentinel.degrade."));
            boolean hasParamRuleChange = propertyNames.stream().anyMatch(k -> k.startsWith("sentinel.param."));
            boolean hasSystemRuleChange = propertyNames.stream().anyMatch(k -> k.startsWith("sentinel.system."));

            if (hasFlowRuleChange) {
                flowRuleService.syncAllRulesToRedis();
            }
            if (hasDegradeRuleChange) {
                degradeRuleService.syncAllRulesToRedis();
            }
            if (hasParamRuleChange) {
                paramFlowRuleService.syncAllRulesToRedis();
            }
            if (hasSystemRuleChange) {
                systemRuleService.syncAllRulesToRedis();
            }

            log.info("Apollo rules sync completed");
        } catch (Exception e) {
            log.error("Failed to sync rules from Apollo", e);
        }
    }

    public String getConfig(String key, String defaultValue) {
        return config.getProperty(key, defaultValue);
    }

    public Integer getIntConfig(String key, Integer defaultValue) {
        return config.getIntProperty(key, defaultValue);
    }

    public Double getDoubleConfig(String key, Double defaultValue) {
        return config.getDoubleProperty(key, defaultValue);
    }

    public Boolean getBooleanConfig(String key, Boolean defaultValue) {
        return config.getBooleanProperty(key, defaultValue);
    }
}
