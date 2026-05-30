package com.hotconfig.core.source;

import com.ctrip.framework.apollo.Config;
import com.ctrip.framework.apollo.ConfigChangeListener;
import com.ctrip.framework.apollo.ConfigService;
import com.ctrip.framework.apollo.enums.PropertyChangeType;
import com.ctrip.framework.apollo.model.ConfigChangeEvent;
import com.hotconfig.core.event.ConfigChange;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class ApolloConfigSource extends AbstractConfigSource {

    private static final Logger logger = LoggerFactory.getLogger(ApolloConfigSource.class);

    public static final String SOURCE_NAME = "apollo";
    public static final int ORDER = 50;

    public static final String DEFAULT_NAMESPACE = "application";

    private final String namespace;
    private final String appId;

    private Config apolloConfig;
    private ConfigChangeListener apolloListener;

    private final Map<String, Object> config = new ConcurrentHashMap<>();

    public ApolloConfigSource() {
        this(DEFAULT_NAMESPACE, null);
    }

    public ApolloConfigSource(String namespace) {
        this(namespace, null);
    }

    public ApolloConfigSource(String namespace, String appId) {
        this.namespace = namespace;
        this.appId = appId;
    }

    @Override
    protected void doInit() throws Exception {
        if (!isApolloAvailable()) {
            logger.warn("Apollo client not available, ApolloConfigSource will be disabled");
            return;
        }

        try {
            if (appId != null) {
                System.setProperty("app.id", appId);
            }

            apolloConfig = ConfigService.getConfig(namespace);
            loadConfig();

            apolloListener = this::onApolloChange;
            apolloConfig.addChangeListener(apolloListener);

            logger.info("ApolloConfigSource initialized for namespace: {}", namespace);
        } catch (Exception e) {
            logger.error("Failed to initialize ApolloConfigSource", e);
            throw e;
        }
    }

    @Override
    protected void doDestroy() throws Exception {
        if (apolloConfig != null && apolloListener != null) {
            apolloConfig.removeChangeListener(apolloListener);
        }
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
        return SOURCE_NAME + ":" + namespace;
    }

    @Override
    public boolean isAvailable() {
        return super.isAvailable() && apolloConfig != null;
    }

    private void loadConfig() {
        if (apolloConfig == null) {
            return;
        }

        config.clear();
        Set<String> propertyNames = apolloConfig.getPropertyNames();
        for (String name : propertyNames) {
            String value = apolloConfig.getProperty(name, null);
            if (value != null) {
                config.put(name, value);
            }
        }
        logger.info("Loaded {} properties from Apollo namespace: {}", config.size(), namespace);
    }

    private void onApolloChange(ConfigChangeEvent event) {
        logger.info("Received Apollo config change event for namespace: {}, changed keys: {}",
                event.getNamespace(), event.changedKeys());

        Map<String, ConfigChange> changes = new HashMap<>();

        for (String key : event.changedKeys()) {
            com.ctrip.framework.apollo.model.ConfigChange change = event.getChange(key);
            ConfigChange.ChangeType changeType = convertChangeType(change.getChangeType());

            ConfigChange configChange = new ConfigChange(
                    key,
                    change.getOldValue(),
                    change.getNewValue(),
                    changeType
            );
            changes.put(key, configChange);

            switch (changeType) {
                case ADDED:
                case MODIFIED:
                    config.put(key, change.getNewValue());
                    break;
                case DELETED:
                    config.remove(key);
                    break;
            }
        }

        if (!changes.isEmpty()) {
            com.hotconfig.core.event.ConfigChangeEvent ourEvent =
                    new com.hotconfig.core.event.ConfigChangeEvent(getSourceName(), changes, this);
            fireChangeEvent(ourEvent);
        }
    }

    private ConfigChange.ChangeType convertChangeType(PropertyChangeType type) {
        switch (type) {
            case ADDED:
                return ConfigChange.ChangeType.ADDED;
            case MODIFIED:
                return ConfigChange.ChangeType.MODIFIED;
            case DELETED:
                return ConfigChange.ChangeType.DELETED;
            default:
                return ConfigChange.ChangeType.MODIFIED;
        }
    }

    public static boolean isApolloAvailable() {
        try {
            Class.forName("com.ctrip.framework.apollo.ConfigService");
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }

    public void refresh() {
        loadConfig();
    }
}
