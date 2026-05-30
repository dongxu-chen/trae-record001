package com.hotconfig.core.source;

import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.listener.ConfigChangeListener;

import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;

public class CompositeConfigSource extends AbstractConfigSource {

    public static final String SOURCE_NAME = "composite";
    public static final int ORDER = 0;

    private final List<ConfigSource> sources = new CopyOnWriteArrayList<>();

    private final ConfigChangeListener delegateListener = this::onSourceChange;

    public CompositeConfigSource() {
    }

    public CompositeConfigSource(List<ConfigSource> sources) {
        this.sources.addAll(sources);
    }

    public void addSource(ConfigSource source) {
        if (source != null && !sources.contains(source)) {
            sources.add(source);
            source.addChangeListener(delegateListener);
            sortSources();
        }
    }

    public void removeSource(ConfigSource source) {
        if (source != null) {
            sources.remove(source);
            source.removeChangeListener(delegateListener);
        }
    }

    public List<ConfigSource> getSources() {
        return Collections.unmodifiableList(sources);
    }

    private void sortSources() {
        sources.sort(Comparator.comparingInt(ConfigSource::getOrder));
    }

    @Override
    protected void doInit() throws Exception {
        for (ConfigSource source : sources) {
            source.init();
            source.addChangeListener(delegateListener);
        }
        sortSources();
    }

    @Override
    protected void doDestroy() throws Exception {
        for (ConfigSource source : sources) {
            try {
                source.removeChangeListener(delegateListener);
                source.destroy();
            } catch (Exception e) {
                logger.error("Failed to destroy config source: {}", source.getName(), e);
            }
        }
        sources.clear();
    }

    @Override
    public int getOrder() {
        return ORDER;
    }

    @Override
    public Object getValue(String key) {
        for (ConfigSource source : sources) {
            if (source.isAvailable() && source.containsKey(key)) {
                return source.getValue(key);
            }
        }
        return null;
    }

    @Override
    public Map<String, Object> getAllConfig() {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int i = sources.size() - 1; i >= 0; i--) {
            ConfigSource source = sources.get(i);
            if (source.isAvailable()) {
                result.putAll(source.getAllConfig());
            }
        }
        return result;
    }

    @Override
    public Set<String> getPropertyNames() {
        Set<String> names = new LinkedHashSet<>();
        for (ConfigSource source : sources) {
            if (source.isAvailable()) {
                names.addAll(source.getPropertyNames());
            }
        }
        return names;
    }

    @Override
    public boolean containsKey(String key) {
        for (ConfigSource source : sources) {
            if (source.isAvailable() && source.containsKey(key)) {
                return true;
            }
        }
        return false;
    }

    @Override
    protected String getSourceName() {
        return SOURCE_NAME;
    }

    @Override
    public boolean isAvailable() {
        return super.isAvailable() && !sources.isEmpty() &&
                sources.stream().anyMatch(ConfigSource::isAvailable);
    }

    private void onSourceChange(ConfigChangeEvent event) {
        logger.debug("Received change event from source: {}, forwarding to composite listeners",
                event.getSourceName());
        fireChangeEvent(event);
    }

    public void refreshAll() {
        for (ConfigSource source : sources) {
            if (source.isAvailable()) {
                try {
                    if (source instanceof FileConfigSource) {
                        ((FileConfigSource) source).refresh();
                    } else if (source instanceof EnvironmentConfigSource) {
                        ((EnvironmentConfigSource) source).refresh();
                    } else if (source instanceof ApolloConfigSource) {
                        ((ApolloConfigSource) source).refresh();
                    }
                } catch (Exception e) {
                    logger.error("Failed to refresh config source: {}", source.getName(), e);
                }
            }
        }
    }
}
