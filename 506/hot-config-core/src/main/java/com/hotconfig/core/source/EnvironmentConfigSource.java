package com.hotconfig.core.source;

import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class EnvironmentConfigSource extends AbstractConfigSource {

    public static final String SOURCE_NAME = "environment";
    public static final int ORDER = 100;

    private final Map<String, Object> config = new ConcurrentHashMap<>();

    private final boolean includeSystemProperties;
    private final boolean includeSystemEnvironment;

    public EnvironmentConfigSource() {
        this(true, true);
    }

    public EnvironmentConfigSource(boolean includeSystemProperties, boolean includeSystemEnvironment) {
        this.includeSystemProperties = includeSystemProperties;
        this.includeSystemEnvironment = includeSystemEnvironment;
    }

    @Override
    protected void doInit() throws Exception {
        loadConfig();
    }

    @Override
    protected void doDestroy() throws Exception {
        config.clear();
    }

    @Override
    public int getOrder() {
        return ORDER;
    }

    @Override
    public Object getValue(String key) {
        return config.get(key);
    }

    @Override
    public Map<String, Object> getAllConfig() {
        return new HashMap<>(config);
    }

    @Override
    public Set<String> getPropertyNames() {
        return config.keySet();
    }

    @Override
    public boolean containsKey(String key) {
        return config.containsKey(key);
    }

    @Override
    protected String getSourceName() {
        return SOURCE_NAME;
    }

    private void loadConfig() {
        config.clear();

        if (includeSystemProperties) {
            Properties properties = System.getProperties();
            for (String name : properties.stringPropertyNames()) {
                config.put(name, properties.getProperty(name));
            }
            logger.debug("Loaded {} system properties", properties.size());
        }

        if (includeSystemEnvironment) {
            Map<String, String> env = System.getenv();
            for (Map.Entry<String, String> entry : env.entrySet()) {
                String key = entry.getKey();
                String value = entry.getValue();
                config.put(key, value);
                config.put(key.toLowerCase().replace('_', '.'), value);
            }
            logger.debug("Loaded {} environment variables", env.size());
        }

        logger.info("EnvironmentConfigSource initialized with {} properties", config.size());
    }

    public void refresh() {
        loadConfig();
    }
}
