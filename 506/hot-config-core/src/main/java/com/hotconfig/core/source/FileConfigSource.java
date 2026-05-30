package com.hotconfig.core.source;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.hotconfig.core.event.ConfigChange;
import com.hotconfig.core.event.ConfigChangeEvent;
import org.yaml.snakeyaml.Yaml;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

import static java.nio.file.StandardWatchEventKinds.*;

public class FileConfigSource extends AbstractConfigSource {

    public static final String SOURCE_NAME = "file";
    public static final int ORDER = 200;

    private final String filePath;
    private final FileType fileType;
    private final boolean enableWatch;

    private final Map<String, Object> config = new ConcurrentHashMap<>();

    private WatchService watchService;
    private Thread watchThread;
    private volatile long lastModified = 0;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Yaml yaml = new Yaml();

    public FileConfigSource(String filePath) {
        this(filePath, true);
    }

    public FileConfigSource(String filePath, boolean enableWatch) {
        this.filePath = filePath;
        this.enableWatch = enableWatch;
        this.fileType = detectFileType(filePath);
    }

    @Override
    protected void doInit() throws Exception {
        File file = new File(filePath);
        if (!file.exists()) {
            logger.warn("Config file not found: {}", filePath);
            return;
        }

        loadConfig();
        lastModified = file.lastModified();

        if (enableWatch) {
            startFileWatcher();
        }
    }

    @Override
    protected void doDestroy() throws Exception {
        if (watchThread != null && watchThread.isAlive()) {
            watchThread.interrupt();
        }
        if (watchService != null) {
            watchService.close();
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
        return SOURCE_NAME + ":" + filePath;
    }

    private FileType detectFileType(String path) {
        if (path.endsWith(".properties")) {
            return FileType.PROPERTIES;
        } else if (path.endsWith(".yml") || path.endsWith(".yaml")) {
            return FileType.YAML;
        } else if (path.endsWith(".json")) {
            return FileType.JSON;
        }
        throw new IllegalArgumentException("Unsupported config file type: " + path);
    }

    @SuppressWarnings("unchecked")
    private void loadConfig() {
        Map<String, Object> oldConfig = new HashMap<>(config);
        config.clear();

        try (FileInputStream fis = new FileInputStream(filePath)) {
            Map<String, Object> loadedConfig;
            switch (fileType) {
                case PROPERTIES:
                    Properties properties = new Properties();
                    properties.load(fis);
                    loadedConfig = new HashMap<>((Map) properties);
                    break;
                case YAML:
                    loadedConfig = yaml.load(fis);
                    if (loadedConfig == null) {
                        loadedConfig = new HashMap<>();
                    }
                    break;
                case JSON:
                    loadedConfig = objectMapper.readValue(fis, Map.class);
                    break;
                default:
                    throw new IllegalArgumentException("Unsupported file type");
            }

            flattenMap("", loadedConfig, config);
            logger.info("Loaded {} properties from file: {}", config.size(), filePath);

            if (!oldConfig.isEmpty()) {
                Map<String, ConfigChange> changes = detectChanges(oldConfig, config);
                if (!changes.isEmpty()) {
                    ConfigChangeEvent event = new ConfigChangeEvent(getSourceName(), changes, this);
                    fireChangeEvent(event);
                }
            }
        } catch (Exception e) {
            logger.error("Failed to load config from file: {}", filePath, e);
            config.putAll(oldConfig);
        }
    }

    @SuppressWarnings("unchecked")
    private void flattenMap(String prefix, Map<String, Object> source, Map<String, Object> target) {
        for (Map.Entry<String, Object> entry : source.entrySet()) {
            String key = prefix.isEmpty() ? entry.getKey() : prefix + "." + entry.getKey();
            Object value = entry.getValue();

            if (value instanceof Map) {
                flattenMap(key, (Map<String, Object>) value, target);
            } else if (value instanceof List) {
                target.put(key, value);
            } else {
                target.put(key, value);
            }
        }
    }

    private Map<String, ConfigChange> detectChanges(Map<String, Object> oldConfig, Map<String, Object> newConfig) {
        Map<String, ConfigChange> changes = new HashMap<>();

        Set<String> allKeys = new HashSet<>();
        allKeys.addAll(oldConfig.keySet());
        allKeys.addAll(newConfig.keySet());

        for (String key : allKeys) {
            Object oldValue = oldConfig.get(key);
            Object newValue = newConfig.get(key);

            if (!oldConfig.containsKey(key)) {
                changes.put(key, new ConfigChange(key, null, newValue, ConfigChange.ChangeType.ADDED));
            } else if (!newConfig.containsKey(key)) {
                changes.put(key, new ConfigChange(key, oldValue, null, ConfigChange.ChangeType.DELETED));
            } else if (!Objects.equals(oldValue, newValue)) {
                changes.put(key, new ConfigChange(key, oldValue, newValue, ConfigChange.ChangeType.MODIFIED));
            }
        }

        return changes;
    }

    private void startFileWatcher() throws IOException {
        Path path = Paths.get(filePath);
        Path dir = path.getParent();
        if (dir == null) {
            dir = Paths.get(".");
        }

        watchService = FileSystems.getDefault().newWatchService();
        dir.register(watchService, ENTRY_MODIFY, ENTRY_CREATE, ENTRY_DELETE);

        final Path fileName = path.getFileName();

        watchThread = new Thread(() -> {
            try {
                while (!Thread.currentThread().isInterrupted()) {
                    WatchKey key = watchService.poll(5, TimeUnit.SECONDS);
                    if (key == null) {
                        continue;
                    }

                    for (WatchEvent<?> event : key.pollEvents()) {
                        WatchEvent.Kind<?> kind = event.kind();
                        if (kind == OVERFLOW) {
                            continue;
                        }

                        Path changed = (Path) event.context();
                        if (changed != null && changed.getFileName().equals(fileName)) {
                            File file = new File(filePath);
                            if (file.exists() && file.lastModified() > lastModified) {
                                lastModified = file.lastModified();
                                logger.info("Config file changed: {}", filePath);
                                loadConfig();
                            }
                        }
                    }

                    if (!key.reset()) {
                        break;
                    }
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                logger.debug("File watcher interrupted");
            } catch (Exception e) {
                logger.error("File watcher error", e);
            }
        }, "hot-config-file-watcher-" + fileName);
        watchThread.setDaemon(true);
        watchThread.start();

        logger.info("Started file watcher for: {}", filePath);
    }

    public void refresh() {
        loadConfig();
    }

    public enum FileType {
        PROPERTIES,
        YAML,
        JSON
    }
}
