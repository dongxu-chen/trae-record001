package com.hotconfig.core.source;

import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.listener.ConfigChangeListener;

import java.util.Map;
import java.util.Set;

public interface ConfigSource {

    String getName();

    int getOrder();

    Object getValue(String key);

    Map<String, Object> getAllConfig();

    Set<String> getPropertyNames();

    boolean containsKey(String key);

    void addChangeListener(ConfigChangeListener listener);

    void removeChangeListener(ConfigChangeListener listener);

    void fireChangeEvent(ConfigChangeEvent event);

    void init();

    void destroy();

    boolean isAvailable();
}
