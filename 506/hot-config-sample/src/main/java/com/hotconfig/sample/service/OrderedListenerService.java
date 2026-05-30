package com.hotconfig.sample.service;

import com.hotconfig.annotation.ConfigListener;
import com.hotconfig.annotation.DependsOnConfig;
import com.hotconfig.core.event.ConfigChangeEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class OrderedListenerService {

    private static final Logger logger = LoggerFactory.getLogger(OrderedListenerService.class);

    private final List<String> executionOrder = new ArrayList<>();

    private int cacheSize = 0;
    private int connectionPoolSize = 0;
    private int timeout = 0;

    @ConfigListener(keys = "order.test.first")
    @DependsOnConfig(order = 1, value = "order.test.first")
    public void onFirstChange(ConfigChangeEvent event) {
        logger.info("First listener executed (order=1), changed: {}", event.getChangedKeys());
        executionOrder.add("first");
        String value = (String) event.getChange("order.test.first").getNewValue();
        cacheSize = Integer.parseInt(value);
        logger.info("Cache size updated to: {}", cacheSize);
    }

    @ConfigListener(keys = "order.test.second")
    @DependsOnConfig(order = 2, value = "order.test.second")
    public void onSecondChange(ConfigChangeEvent event) {
        logger.info("Second listener executed (order=2), changed: {}", event.getChangedKeys());
        executionOrder.add("second");
        String value = (String) event.getChange("order.test.second").getNewValue();
        connectionPoolSize = Integer.parseInt(value);
        logger.info("Connection pool size updated to: {}", connectionPoolSize);
    }

    @ConfigListener(keys = "order.test.third")
    @DependsOnConfig(order = 3, value = {"order.test.first", "order.test.second", "order.test.third"})
    public void onThirdChange(ConfigChangeEvent event) {
        logger.info("Third listener executed (order=3), changed: {}", event.getChangedKeys());
        executionOrder.add("third");
        String value = (String) event.getChange("order.test.third").getNewValue();
        timeout = Integer.parseInt(value);
        logger.info("Timeout updated to: {}, total config: cacheSize={}, poolSize={}, timeout={}",
                timeout, cacheSize, connectionPoolSize, timeout);
    }

    public List<String> getExecutionOrder() {
        return new ArrayList<>(executionOrder);
    }

    public void clearExecutionOrder() {
        executionOrder.clear();
    }

    public int getCacheSize() {
        return cacheSize;
    }

    public int getConnectionPoolSize() {
        return connectionPoolSize;
    }

    public int getTimeout() {
        return timeout;
    }
}
