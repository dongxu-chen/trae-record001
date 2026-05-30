package com.apiversion.gateway.strategy;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class HeaderParseStrategyFactory {

    private final List<HeaderParseStrategy> strategies;
    private final Map<String, HeaderParseStrategy> strategyMap = new HashMap<>();

    @PostConstruct
    public void init() {
        for (HeaderParseStrategy strategy : strategies) {
            strategyMap.put(strategy.getStrategyName().toUpperCase(), strategy);
        }
        log.info("已注册Header解析策略: {}", strategyMap.keySet());
    }

    public HeaderParseStrategy getStrategy(String strategyName) {
        if (strategyName == null) {
            return strategyMap.get("DIRECT");
        }
        return strategyMap.getOrDefault(strategyName.toUpperCase(), strategyMap.get("DIRECT"));
    }

    public boolean exists(String strategyName) {
        if (strategyName == null) {
            return false;
        }
        return strategyMap.containsKey(strategyName.toUpperCase());
    }
}
