package com.hotconfig.sample;

import com.hotconfig.sample.config.AppConfig;
import com.hotconfig.sample.controller.ConfigController;
import com.hotconfig.sample.service.ConfigService;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit4.SpringRunner;

import java.util.Map;

import static org.junit.Assert.*;

@RunWith(SpringRunner.class)
@SpringBootTest
public class HotConfigSpringTest {

    @Autowired
    private AppConfig appConfig;

    @Autowired
    private ConfigService configService;

    @Autowired
    private ConfigController configController;

    @Test
    public void testContextLoads() {
        assertNotNull(appConfig);
        assertNotNull(configService);
        assertNotNull(configController);
    }

    @Test
    public void testAppConfigInjected() {
        assertNotNull(appConfig.getAppName());
        assertNotNull(appConfig.getVersion());
        assertNotNull(appConfig.getEnv());
        assertNotNull(appConfig.getConnectionTimeout());
        assertNotNull(appConfig.getMaxConnections());
        assertNotNull(appConfig.getCacheTtl());
        assertNotNull(appConfig.getThreshold());
        assertNotNull(appConfig.getAllowedIps());
    }

    @Test
    public void testConfigService() {
        assertNotNull(configService.getAppConfig());
        assertNotNull(configService.getCustomMessage());
    }

    @Test
    public void testConfigController() {
        AppConfig result = configController.getAppConfig();
        assertNotNull(result);
        assertEquals(appConfig.getAppName(), result.getAppName());

        Object version = configController.getAppConfigField("version");
        assertEquals(appConfig.getVersion(), version);

        String customMessage = configController.getCustomMessage();
        assertEquals(configService.getCustomMessage(), customMessage);

        Map<String, Object> snapshot = configController.getConfigSnapshot();
        assertNotNull(snapshot);
        assertFalse(snapshot.isEmpty());
    }

    @Test
    public void testConfigManagerInService() {
        configService.setLocalConfig("test.key", "test.value");
        String value = configService.getConfigValue("test.key");
        assertEquals("test.value", value);
    }

    @Test
    public void testRefreshConfig() {
        Map<String, String> result = configController.refreshConfig();
        assertEquals("success", result.get("status"));
    }

    @Test
    public void testLocalConfigEndpoint() {
        Map<String, String> result = configController.setLocalConfig("local.test", "local.value");
        assertEquals("success", result.get("status"));
        assertEquals("local.test", result.get("key"));
        assertEquals("local.value", result.get("value"));

        String value = configController.getConfigValue("local.test");
        assertEquals("local.value", value);
    }

    @Test
    public void testTypedConfigValue() {
        configService.setLocalConfig("typed.int", "123");
        configService.setLocalConfig("typed.long", "456");
        configService.setLocalConfig("typed.boolean", "true");
        configService.setLocalConfig("typed.double", "3.14");

        assertEquals(Integer.valueOf(123), configController.getConfigValueTyped("typed.int", "int"));
        assertEquals(Long.valueOf(456L), configController.getConfigValueTyped("typed.long", "long"));
        assertEquals(Boolean.TRUE, configController.getConfigValueTyped("typed.boolean", "boolean"));
        assertEquals(Double.valueOf(3.14), configController.getConfigValueTyped("typed.double", "double"));
    }
}
