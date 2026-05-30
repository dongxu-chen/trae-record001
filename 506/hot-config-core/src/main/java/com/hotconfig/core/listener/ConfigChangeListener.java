package com.hotconfig.core.listener;

import com.hotconfig.core.event.ConfigChangeEvent;

import java.util.function.Consumer;

public interface ConfigChangeListener {

    void onChange(ConfigChangeEvent event);

    default boolean support(ConfigChangeEvent event) {
        return true;
    }

    static ConfigChangeListener of(Consumer<ConfigChangeEvent> consumer) {
        return consumer::accept;
    }

    abstract class KeyBasedListener implements ConfigChangeListener {

        private final String[] keys;

        public KeyBasedListener(String... keys) {
            this.keys = keys;
        }

        @Override
        public boolean support(ConfigChangeEvent event) {
            if (keys == null || keys.length == 0) {
                return true;
            }
            for (String key : keys) {
                if (event.isKeyChanged(key)) {
                    return true;
                }
            }
            return false;
        }
    }

    abstract class PrefixBasedListener implements ConfigChangeListener {

        private final String[] prefixes;

        public PrefixBasedListener(String... prefixes) {
            this.prefixes = prefixes;
        }

        @Override
        public boolean support(ConfigChangeEvent event) {
            if (prefixes == null || prefixes.length == 0) {
                return true;
            }
            for (String prefix : prefixes) {
                if (event.isPrefixChanged(prefix)) {
                    return true;
                }
            }
            return false;
        }
    }
}
