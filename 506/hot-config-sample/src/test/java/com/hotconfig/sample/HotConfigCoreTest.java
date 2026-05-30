package com.hotconfig.sample;

import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.convert.TypeConverter;
import com.hotconfig.core.event.ConfigChange;
import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.listener.ConfigChangeListener;
import com.hotconfig.core.refresh.BeanPropertyRefresher;
import com.hotconfig.sample.config.AppConfig;
import org.junit.Before;
import org.junit.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

public class HotConfigCoreTest {

    private ConfigManager configManager;

    @Before
    public void setUp() {
        configManager = ConfigManager.getInstance();
        if (!configManager.isInitialized()) {
            configManager.init();
        }
        configManager.clearLocalCache();
    }

    @Test
    public void testConfigManagerGetValue() {
        configManager.setLocalValue("test.string", "hello");
        configManager.setLocalValue("test.int", "123");
        configManager.setLocalValue("test.boolean", "true");

        assertEquals("hello", configManager.getString("test.string"));
        assertEquals(Integer.valueOf(123), configManager.getInt("test.int"));
        assertEquals(Boolean.TRUE, configManager.getBoolean("test.boolean"));
    }

    @Test
    public void testTypeConverter() {
        assertEquals(Integer.valueOf(123), TypeConverter.convert("123", Integer.class));
        assertEquals(Long.valueOf(123L), TypeConverter.convert("123", Long.class));
        assertEquals(Boolean.TRUE, TypeConverter.convert("true", Boolean.class));
        assertEquals(Double.valueOf(3.14), TypeConverter.convert("3.14", Double.class));
    }

    @Test
    public void testTypeConverterWithDefault() {
        assertEquals(Integer.valueOf(100), TypeConverter.convert(null, Integer.class, "100"));
        assertEquals("default", TypeConverter.convert("", String.class, "default"));
    }

    @Test
    public void testConfigChangeListener() {
        configManager.setLocalValue("test.key", "oldValue");

        final boolean[] received = {false};
        final String[] newValue = {null};

        ConfigChangeListener listener = new ConfigChangeListener.KeyBasedListener("test.key") {
            @Override
            public void onChange(ConfigChangeEvent event) {
                received[0] = true;
                newValue[0] = (String) event.getChange("test.key").getNewValue();
            }
        };

        configManager.addListener("test.key", listener);

        Map<String, ConfigChange> changes = new HashMap<>();
        changes.put("test.key", new ConfigChange("test.key", "oldValue", "newValue", ConfigChange.ChangeType.MODIFIED));
        ConfigChangeEvent event = new ConfigChangeEvent("test", changes, this);
        configManager.getConfigSources().get(0).fireChangeEvent(event);

        assertTrue(received[0]);
        assertEquals("newValue", newValue[0]);
    }

    @Test
    public void testBeanPropertyRefresher() {
        AppConfig appConfig = new AppConfig();
        appConfig.setAppName("oldName");
        appConfig.setVersion("1.0.0");

        configManager.setLocalValue("app.name", "newName");
        configManager.setLocalValue("app.version", "2.0.0");

        BeanPropertyRefresher refresher = new BeanPropertyRefresher();
        refresher.registerBean(appConfig);
        refresher.refreshBean(appConfig);

        assertEquals("newName", appConfig.getAppName());
        assertEquals("2.0.0", appConfig.getVersion());
    }

    @Test
    public void testConfigManagerDefaultValue() {
        String value = configManager.getString("non.existent.key", "defaultValue");
        assertEquals("defaultValue", value);

        Integer intValue = configManager.getInt("non.existent.int", 456);
        assertEquals(Integer.valueOf(456), intValue);
    }

    @Test
    public void testPrefixListener() {
        final boolean[] received = {false};
        ConfigChangeListener listener = new ConfigChangeListener.PrefixBasedListener("test.prefix") {
            @Override
            public void onChange(ConfigChangeEvent event) {
                received[0] = true;
            }
        };

        configManager.addPrefixListener("test.prefix", listener);

        Map<String, ConfigChange> changes = new HashMap<>();
        changes.put("test.prefix.key", new ConfigChange("test.prefix.key", null, "value", ConfigChange.ChangeType.ADDED));
        ConfigChangeEvent event = new ConfigChangeEvent("test", changes, this);
        configManager.getConfigSources().get(0).fireChangeEvent(event);

        assertTrue(received[0]);
    }

    @Test
    public void testConfigChangeTypes() {
        Map<String, ConfigChange> changes = new HashMap<>();
        changes.put("added.key", new ConfigChange("added.key", null, "value", ConfigChange.ChangeType.ADDED));
        changes.put("modified.key", new ConfigChange("modified.key", "old", "new", ConfigChange.ChangeType.MODIFIED));
        changes.put("deleted.key", new ConfigChange("deleted.key", "value", null, ConfigChange.ChangeType.DELETED));

        ConfigChangeEvent event = new ConfigChangeEvent("test", changes, this);

        assertTrue(event.isKeyChanged("added.key"));
        assertTrue(event.isKeyChanged("modified.key"));
        assertTrue(event.isKeyChanged("deleted.key"));
        assertFalse(event.isKeyChanged("other.key"));

        assertTrue(event.isPrefixChanged("added."));
        assertTrue(event.isPrefixChanged("modified."));

        assertEquals(ConfigChange.ChangeType.ADDED, event.getChange("added.key").getChangeType());
        assertEquals(ConfigChange.ChangeType.MODIFIED, event.getChange("modified.key").getChangeType());
        assertEquals(ConfigChange.ChangeType.DELETED, event.getChange("deleted.key").getChangeType());
    }

    @Test
    public void testRefreshAll() {
        configManager.setLocalValue("refresh.test", "value1");

        assertEquals("value1", configManager.getLocalValue("refresh.test"));

        configManager.refresh();

        assertNull(configManager.getLocalValue("refresh.test"));
    }
}
