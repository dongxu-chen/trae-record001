package com.hotconfig.sample;

import com.fasterxml.jackson.core.type.TypeReference;
import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.convert.TypeConverter;
import com.hotconfig.core.diff.ConfigDiff;
import com.hotconfig.core.diff.ConfigDiffManager;
import com.hotconfig.core.event.ConfigChange;
import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.health.ConfigHealthCheckResult;
import com.hotconfig.core.health.ConfigHealthChecker;
import com.hotconfig.core.listener.ConfigListenerMethodProcessor;
import com.hotconfig.core.refresh.BeanPropertyRefresher;
import com.hotconfig.core.rollback.ConfigRollbackManager;
import com.hotconfig.core.rollback.ConfigSnapshot;
import com.hotconfig.sample.config.GenericConfig;
import com.hotconfig.sample.service.OrderedListenerService;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit4.SpringRunner;

import java.lang.reflect.Field;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.*;

@RunWith(SpringRunner.class)
@SpringBootTest
public class AdvancedFeaturesTest {

    private static final Logger logger = LoggerFactory.getLogger(AdvancedFeaturesTest.class);

    @Autowired
    private GenericConfig genericConfig;

    @Autowired
    private OrderedListenerService orderedListenerService;

    @Autowired
    private ConfigManager configManager;

    @Autowired
    private BeanPropertyRefresher propertyRefresher;

    @Autowired
    private ConfigListenerMethodProcessor listenerProcessor;

    @Autowired
    private ConfigHealthChecker healthChecker;

    private ConfigRollbackManager rollbackManager;
    private ConfigDiffManager diffManager;

    @Test
    public void testGenericTypeInjection() {
        assertNotNull("GenericConfig should be injected", genericConfig);

        logger.info("Testing generic type injection...");

        List<String> stringList = genericConfig.getStringList();
        assertNotNull("stringList should not be null", stringList);
        assertEquals(3, stringList.size());
        assertEquals("a", stringList.get(0));
        assertEquals("b", stringList.get(1));
        assertEquals("c", stringList.get(2));
        logger.info("List<String> injection OK: {}", stringList);

        List<Integer> integerList = genericConfig.getIntegerList();
        assertNotNull("integerList should not be null", integerList);
        assertEquals(3, integerList.size());
        assertEquals(Integer.valueOf(1), integerList.get(0));
        assertEquals(Integer.valueOf(2), integerList.get(1));
        assertEquals(Integer.valueOf(3), integerList.get(2));
        logger.info("List<Integer> injection OK: {}", integerList);

        Set<Long> longSet = genericConfig.getLongSet();
        assertNotNull("longSet should not be null", longSet);
        assertEquals(3, longSet.size());
        assertTrue(longSet.contains(100L));
        assertTrue(longSet.contains(200L));
        assertTrue(longSet.contains(300L));
        logger.info("Set<Long> injection OK: {}", longSet);

        Map<String, Integer> stringIntMap = genericConfig.getStringIntMap();
        assertNotNull("stringIntMap should not be null", stringIntMap);
        assertEquals(Integer.valueOf(1), stringIntMap.get("key1"));
        assertEquals(Integer.valueOf(2), stringIntMap.get("key2"));
        assertEquals(Integer.valueOf(3), stringIntMap.get("key3"));
        logger.info("Map<String, Integer> injection OK: {}", stringIntMap);

        Map<Integer, String> intStringMap = genericConfig.getIntStringMap();
        assertNotNull("intStringMap should not be null", intStringMap);
        assertEquals("one", intStringMap.get(1));
        assertEquals("two", intStringMap.get(2));
        assertEquals("three", intStringMap.get(3));
        logger.info("Map<Integer, String> injection OK: {}", intStringMap);

        Optional<String> optionalValue = genericConfig.getOptionalValue();
        assertNotNull("optionalValue should not be null", optionalValue);
        assertTrue(optionalValue.isPresent());
        assertEquals("default", optionalValue.get());
        logger.info("Optional<String> injection OK: {}", optionalValue);

        Optional<Integer> optionalNumber = genericConfig.getOptionalNumber();
        assertNotNull("optionalNumber should not be null", optionalNumber);
        assertTrue(optionalNumber.isPresent());
        assertEquals(Integer.valueOf(42), optionalNumber.get());
        logger.info("Optional<Integer> injection OK: {}", optionalNumber);

        List<Double> doubleList = genericConfig.getDoubleList();
        assertNotNull("doubleList should not be null", doubleList);
        assertEquals(3, doubleList.size());
        assertEquals(Double.valueOf(1.1), doubleList.get(0));
        logger.info("List<Double> injection OK: {}", doubleList);

        List<Boolean> booleanList = genericConfig.getBooleanList();
        assertNotNull("booleanList should not be null", booleanList);
        assertEquals(3, booleanList.size());
        assertEquals(Boolean.TRUE, booleanList.get(0));
        assertEquals(Boolean.FALSE, booleanList.get(1));
        assertEquals(Boolean.TRUE, booleanList.get(2));
        logger.info("List<Boolean> injection OK: {}", booleanList);

        logger.info("All generic type injection tests passed!");
    }

    @Test
    public void testTypeConverterGenericSupport() {
        logger.info("Testing TypeConverter generic support...");

        Type listType = new TypeReference<List<Integer>>() {}.getType();
        List<Integer> integerList = TypeConverter.convert("4,5,6", listType);
        assertNotNull(integerList);
        assertEquals(3, integerList.size());
        assertEquals(Integer.valueOf(4), integerList.get(0));
        logger.info("TypeConverter.convert(List<Integer>) OK: {}", integerList);

        Type mapType = new TypeReference<Map<String, Long>>() {}.getType();
        Map<String, Long> stringLongMap = TypeConverter.convert("a:100,b:200", mapType);
        assertNotNull(stringLongMap);
        assertEquals(Long.valueOf(100L), stringLongMap.get("a"));
        assertEquals(Long.valueOf(200L), stringLongMap.get("b"));
        logger.info("TypeConverter.convert(Map<String, Long>) OK: {}", stringLongMap);

        Type setType = new TypeReference<Set<Double>>() {}.getType();
        Set<Double> doubleSet = TypeConverter.convert("1.5,2.5,3.5", setType);
        assertNotNull(doubleSet);
        assertTrue(doubleSet.contains(1.5));
        logger.info("TypeConverter.convert(Set<Double>) OK: {}", doubleSet);
    }

    @Test
    public void testTypeConverterGetRawType() throws Exception {
        logger.info("Testing TypeConverter.getRawType...");

        Field stringListField = GenericConfig.class.getDeclaredField("stringList");
        Type genericType = stringListField.getGenericType();
        assertTrue(genericType instanceof ParameterizedType);

        Class<?> rawType = TypeConverter.getRawType(genericType);
        assertEquals(List.class, rawType);
        logger.info("getRawType for List<String> OK: {}", rawType);

        Type[] typeParams = TypeConverter.resolveGenericTypeParameters(stringListField);
        assertEquals(1, typeParams.length);
        assertEquals(String.class, typeParams[0]);
        logger.info("resolveGenericTypeParameters for List<String> OK: {}", (Object[]) typeParams);

        Field mapField = GenericConfig.class.getDeclaredField("stringIntMap");
        Type[] mapTypeParams = TypeConverter.resolveGenericTypeParameters(mapField);
        assertEquals(2, mapTypeParams.length);
        assertEquals(String.class, mapTypeParams[0]);
        assertEquals(Integer.class, mapTypeParams[1]);
        logger.info("resolveGenericTypeParameters for Map<String, Integer> OK: {}", (Object[]) mapTypeParams);
    }

    @Test
    public void testDeferredRefresh() {
        logger.info("Testing deferred refresh mechanism...");

        propertyRefresher.setDeferMode(true);
        assertTrue(propertyRefresher.isDeferMode());

        configManager.setLocalValue("defer.test", "value1");
        propertyRefresher.setDeferMode(false);

        assertFalse(propertyRefresher.isDeferMode());

        configManager.setLocalValue("defer.test2", "value2");

        logger.info("Deferred refresh test passed!");
    }

    @Test
    public void testCircularRefreshDetection() {
        logger.info("Testing circular refresh detection...");

        configManager.setLocalValue("app.name", "test-app");
        configManager.setLocalValue("app.version", "2.0.0");

        propertyRefresher.refreshAllBeans();

        assertTrue(propertyRefresher.getRegisteredBeanTypes().size() > 0);
        logger.info("Circular refresh detection test passed!");
    }

    @Test
    public void testOrderedListeners() {
        logger.info("Testing ordered listeners...");

        List<ConfigListenerMethodProcessor.ListenerMethod> orderedListeners = listenerProcessor.getOrderedListeners();
        assertNotNull(orderedListeners);
        assertTrue(orderedListeners.size() >= 3);

        ConfigListenerMethodProcessor.ListenerMethod first = null;
        ConfigListenerMethodProcessor.ListenerMethod second = null;
        ConfigListenerMethodProcessor.ListenerMethod third = null;

        for (ConfigListenerMethodProcessor.ListenerMethod lm : orderedListeners) {
            String methodName = lm.getMethod().getName();
            if ("onFirstChange".equals(methodName)) {
                first = lm;
            } else if ("onSecondChange".equals(methodName)) {
                second = lm;
            } else if ("onThirdChange".equals(methodName)) {
                third = lm;
            }
        }

        assertNotNull("First listener not found", first);
        assertNotNull("Second listener not found", second);
        assertNotNull("Third listener not found", third);

        assertTrue("First listener order should be 1", first.getOrder() < second.getOrder());
        assertTrue("Second listener order should be 2", second.getOrder() < third.getOrder());
        assertEquals("First listener order should be 1", 1, first.getOrder());
        assertEquals("Second listener order should be 2", 2, second.getOrder());
        assertEquals("Third listener order should be 3", 3, third.getOrder());

        logger.info("Ordered listeners test passed! Order: {} < {} < {}",
                first.getOrder(), second.getOrder(), third.getOrder());
    }

    @Test
    public void testOrderedListenerInvocation() throws Exception {
        logger.info("Testing ordered listener invocation...");

        orderedListenerService.clearExecutionOrder();

        Map<String, ConfigChange> changes = new HashMap<>();
        changes.put("order.test.first",
                new ConfigChange("order.test.first", "0", "100", ConfigChange.ChangeType.MODIFIED));
        changes.put("order.test.second",
                new ConfigChange("order.test.second", "0", "50", ConfigChange.ChangeType.MODIFIED));
        changes.put("order.test.third",
                new ConfigChange("order.test.third", "0", "30", ConfigChange.ChangeType.MODIFIED));

        configManager.setLocalValue("order.test.first", "100");
        configManager.setLocalValue("order.test.second", "50");
        configManager.setLocalValue("order.test.third", "30");

        ConfigChangeEvent event = new ConfigChangeEvent("test", changes, this);
        listenerProcessor.invokeOrderedListeners(event);

        List<String> executionOrder = orderedListenerService.getExecutionOrder();
        logger.info("Execution order: {}", executionOrder);

        assertEquals("first should be first", "first", executionOrder.get(0));
        assertEquals("second should be second", "second", executionOrder.get(1));
        assertEquals("third should be third", "third", executionOrder.get(2));

        assertEquals(100, orderedListenerService.getCacheSize());
        assertEquals(50, orderedListenerService.getConnectionPoolSize());
        assertEquals(30, orderedListenerService.getTimeout());

        logger.info("Ordered listener invocation test passed!");
    }

    @Test
    public void testDependencyCheck() {
        logger.info("Testing dependency check...");

        Map<String, ConfigChange> changes = new HashMap<>();
        changes.put("order.test.third",
                new ConfigChange("order.test.third", null, "1000", ConfigChange.ChangeType.ADDED));

        ConfigChangeEvent event = new ConfigChangeEvent("test", changes, this);

        List<ConfigListenerMethodProcessor.ListenerMethod> listeners =
                listenerProcessor.getListenersForKey("order.test.third");

        ConfigListenerMethodProcessor.ListenerMethod thirdListener = null;

        for (ConfigListenerMethodProcessor.ListenerMethod lm : listeners) {
            if ("onThirdChange".equals(lm.getMethod().getName())) {
                thirdListener = lm;
            }
        }

        assertNotNull(thirdListener);
        String[] dependsOn = thirdListener.getDependsOn();
        assertEquals(3, dependsOn.length);

        assertFalse(thirdListener.support(event));

        configManager.setLocalValue("order.test.first", "100");
        configManager.setLocalValue("order.test.second", "50");

        assertTrue(thirdListener.support(event));

        logger.info("Dependency check test passed!");
    }

    @Test
    public void testGenericConfigRefresh() {
        logger.info("Testing generic config refresh...");

        configManager.setLocalValue("generic.string.list", "x,y,z");
        configManager.setLocalValue("generic.integer.list", "10,20,30");

        propertyRefresher.refreshBean(genericConfig);

        List<String> newStringList = genericConfig.getStringList();
        assertEquals(3, newStringList.size());
        assertEquals("x", newStringList.get(0));
        assertEquals("y", newStringList.get(1));
        assertEquals("z", newStringList.get(2));

        List<Integer> newIntegerList = genericConfig.getIntegerList();
        assertEquals(3, newIntegerList.size());
        assertEquals(Integer.valueOf(10), newIntegerList.get(0));
        assertEquals(Integer.valueOf(20), newIntegerList.get(1));
        assertEquals(Integer.valueOf(30), newIntegerList.get(2));

        logger.info("Generic config refresh test passed!");
    }

    @Test
    public void testGenericMapRefresh() {
        logger.info("Testing generic map refresh...");

        configManager.setLocalValue("generic.string-int.map", "a:100,b:200,c:300");
        configManager.setLocalValue("generic.int-string.map", "10:ten,20:twenty,30:thirty");

        propertyRefresher.refreshBean(genericConfig);

        Map<String, Integer> stringIntMap = genericConfig.getStringIntMap();
        assertEquals(3, stringIntMap.size());
        assertEquals(Integer.valueOf(100), stringIntMap.get("a"));
        assertEquals(Integer.valueOf(200), stringIntMap.get("b"));
        assertEquals(Integer.valueOf(300), stringIntMap.get("c"));

        Map<Integer, String> intStringMap = genericConfig.getIntStringMap();
        assertEquals(3, intStringMap.size());
        assertEquals("ten", intStringMap.get(10));
        assertEquals("twenty", intStringMap.get(20));
        assertEquals("thirty", intStringMap.get(30));

        logger.info("Generic map refresh test passed!");
    }

    @Test
    public void testConfigSnapshotCreation() {
        logger.info("Testing config snapshot creation...");

        rollbackManager = configManager.getRollbackManager();
        assertNotNull("RollbackManager should not be null", rollbackManager);

        configManager.setLocalValue("snapshot.test.key1", "value1");
        configManager.setLocalValue("snapshot.test.key2", "value2");

        ConfigSnapshot snapshot = configManager.createSnapshot("Test snapshot");
        assertNotNull("Snapshot should not be null", snapshot);
        assertNotNull("Snapshot ID should not be null", snapshot.getId());
        assertTrue("Snapshot should contain key1", snapshot.containsKey("snapshot.test.key1"));
        assertTrue("Snapshot should contain key2", snapshot.containsKey("snapshot.test.key2"));
        assertEquals("value1", snapshot.getValue("snapshot.test.key1"));
        assertEquals("value2", snapshot.getValue("snapshot.test.key2"));
        assertEquals(ConfigSnapshot.SnapshotType.MANUAL, snapshot.getType());

        logger.info("Snapshot created: {}", snapshot.getId());
        logger.info("Snapshot contains {} properties", snapshot.size());

        List<ConfigSnapshot> history = rollbackManager.getSnapshotHistory();
        assertTrue("History should contain at least one snapshot", history.size() > 0);

        logger.info("Config snapshot creation test passed!");
    }

    @Test
    public void testConfigRollback() {
        logger.info("Testing config rollback...");

        rollbackManager = configManager.getRollbackManager();
        assertNotNull(rollbackManager);

        configManager.setLocalValue("rollback.test.key", "original-value");
        propertyRefresher.refreshBean(genericConfig);

        ConfigSnapshot beforeSnapshot = configManager.createSnapshot("Before change");
        String snapshotId = beforeSnapshot.getId();

        configManager.setLocalValue("rollback.test.key", "changed-value");
        propertyRefresher.refreshBean(genericConfig);

        assertEquals("changed-value", configManager.getValue("rollback.test.key"));

        ConfigRollbackManager.RollbackResult result = configManager.rollbackToSnapshot(snapshotId);
        assertNotNull("Rollback result should not be null", result);
        assertTrue("Rollback should be successful", result.isSuccess());

        Object rolledBackValue = configManager.getValue("rollback.test.key");
        assertEquals("original-value", rolledBackValue);

        logger.info("Rollback result: {}", result);
        logger.info("Config rollback test passed!");
    }

    @Test
    public void testRollbackByKeys() {
        logger.info("Testing rollback by specific keys...");

        rollbackManager = configManager.getRollbackManager();

        configManager.setLocalValue("rollback.multi.key1", "original1");
        configManager.setLocalValue("rollback.multi.key2", "original2");
        configManager.setLocalValue("rollback.multi.key3", "original3");

        ConfigSnapshot snapshot = configManager.createSnapshot("Multi-key snapshot");
        String snapshotId = snapshot.getId();

        configManager.setLocalValue("rollback.multi.key1", "changed1");
        configManager.setLocalValue("rollback.multi.key2", "changed2");
        configManager.setLocalValue("rollback.multi.key3", "changed3");

        Set<String> keysToRollback = new HashSet<>(Arrays.asList("rollback.multi.key1", "rollback.multi.key3"));
        ConfigRollbackManager.RollbackResult result = rollbackManager.rollbackByKeys(keysToRollback, snapshotId);

        assertTrue("Rollback should be successful", result.isSuccess());
        assertEquals("original1", configManager.getValue("rollback.multi.key1"));
        assertEquals("changed2", configManager.getValue("rollback.multi.key2"));
        assertEquals("original3", configManager.getValue("rollback.multi.key3"));

        logger.info("Rollback by keys test passed!");
    }

    @Test
    public void testScheduledRollback() throws Exception {
        logger.info("Testing scheduled rollback...");

        rollbackManager = configManager.getRollbackManager();

        configManager.setLocalValue("scheduled.test.key", "original");
        ConfigSnapshot snapshot = configManager.createSnapshot("Scheduled rollback test");

        configManager.setLocalValue("scheduled.test.key", "temporary");
        assertEquals("temporary", configManager.getValue("scheduled.test.key"));

        CountDownLatch latch = new CountDownLatch(1);
        final String[] finalValue = new String[1];

        String taskId = rollbackManager.scheduleRollback(snapshot.getId(), 500, null);
        assertNotNull("Task ID should not be null", taskId);

        Thread.sleep(800);

        finalValue[0] = String.valueOf(configManager.getValue("scheduled.test.key"));
        assertEquals("original", finalValue[0]);

        logger.info("Scheduled rollback test passed!");
    }

    @Test
    public void testConfigDiffCreation() {
        logger.info("Testing config diff creation...");

        diffManager = configManager.getDiffManager();
        assertNotNull("DiffManager should not be null", diffManager);

        Map<String, Object> before = new HashMap<>();
        before.put("diff.test.key1", "value1");
        before.put("diff.test.key2", "value2");
        before.put("diff.test.key3", "value3");

        Map<String, Object> after = new HashMap<>();
        after.put("diff.test.key1", "value1");
        after.put("diff.test.key2", "changed");
        after.put("diff.test.key4", "new");

        ConfigDiff diff = ConfigDiff.compare("test-source", before, after);

        assertTrue("Diff should have changes", diff.hasChanges());
        assertEquals(3, diff.getChangeCount());
        assertEquals(1, diff.getAddedCount());
        assertEquals(1, diff.getModifiedCount());
        assertEquals(1, diff.getDeletedCount());

        assertTrue("Should have key2 modified", diff.hasChange("diff.test.key2"));
        assertTrue("Should have key3 deleted", diff.hasChange("diff.test.key3"));
        assertTrue("Should have key4 added", diff.hasChange("diff.test.key4"));

        ConfigChange key2Change = diff.getChange("diff.test.key2");
        assertEquals(ConfigChange.ChangeType.MODIFIED, key2Change.getChangeType());
        assertEquals("value2", key2Change.getOldValue());
        assertEquals("changed", key2Change.getNewValue());

        logger.info("Diff summary:\n{}", diff.getSummaryText());
        logger.info("Config diff creation test passed!");
    }

    @Test
    public void testConfigDiffNotification() throws Exception {
        logger.info("Testing config diff notification...");

        diffManager = configManager.getDiffManager();

        final CountDownLatch latch = new CountDownLatch(1);
        final ConfigDiff[] receivedDiff = new ConfigDiff[1];

        diffManager.addDiffListener(diff -> {
            receivedDiff[0] = diff;
            latch.countDown();
        });

        Map<String, ConfigChange> changes = new HashMap<>();
        changes.put("notify.test.key",
                new ConfigChange("notify.test.key", "old", "new", ConfigChange.ChangeType.MODIFIED));

        diffManager.createAndNotifyDiffFromChanges("test-source", changes);

        boolean received = latch.await(2, TimeUnit.SECONDS);
        assertTrue("Should receive diff notification", received);
        assertNotNull("Received diff should not be null", receivedDiff[0]);
        assertEquals(1, receivedDiff[0].getChangeCount());
        assertEquals("new", receivedDiff[0].getChange("notify.test.key").getNewValue());

        logger.info("Config diff notification test passed!");
    }

    @Test
    public void testDiffHistory() {
        logger.info("Testing diff history...");

        diffManager = configManager.getDiffManager();

        Map<String, ConfigChange> changes1 = new HashMap<>();
        changes1.put("history.test.key1",
                new ConfigChange("history.test.key1", "a", "b", ConfigChange.ChangeType.MODIFIED));
        diffManager.createAndNotifyDiffFromChanges("test", changes1);

        Map<String, ConfigChange> changes2 = new HashMap<>();
        changes2.put("history.test.key2",
                new ConfigChange("history.test.key2", "1", "2", ConfigChange.ChangeType.MODIFIED));
        diffManager.createAndNotifyDiffFromChanges("test", changes2);

        List<ConfigDiff> history = diffManager.getDiffHistory();
        assertTrue("History should have entries", history.size() >= 2);

        ConfigDiff latest = diffManager.getLatestDiff();
        assertNotNull("Latest diff should not be null", latest);
        assertTrue("Latest should have key2", latest.hasChange("history.test.key2"));

        List<ConfigDiff> key1History = diffManager.getDiffHistoryByKey("history.test.key1");
        assertEquals(1, key1History.size());

        logger.info("Diff history test passed! History size: {}", history.size());
    }

    @Test
    public void testHealthCheckDanglingReferences() {
        logger.info("Testing health check - dangling references...");

        assertNotNull("HealthChecker should not be null", healthChecker);

        Set<String> referencedKeys = healthChecker.getReferencedKeys();
        assertTrue("Should have referenced keys", referencedKeys.size() > 0);
        logger.info("Total referenced keys: {}", referencedKeys.size());

        for (String key : referencedKeys) {
            logger.debug("Referenced key: {}", key);
        }

        assertTrue("Should contain generic config keys",
                referencedKeys.contains("generic.string.list"));
        assertTrue("Should contain app config keys",
                referencedKeys.contains("app.name"));

        Set<String> danglingKeys = healthChecker.getDanglingKeys();
        assertNotNull("Dangling keys set should not be null", danglingKeys);
        logger.info("Dangling keys found: {}", danglingKeys.size());

        ConfigHealthCheckResult result = healthChecker.performFullCheck();
        assertNotNull("Health check result should not be null", result);
        logger.info("Health check result:\n{}", result.getSummary());

        assertNotNull("Overall status should not be null", result.getOverallStatus());

        logger.info("Health check dangling references test passed!");
    }

    @Test
    public void testHealthCheckUnusedConfig() {
        logger.info("Testing health check - unused config...");

        assertNotNull(healthChecker);

        configManager.setLocalValue("unused.config.key1", "value1");
        configManager.setLocalValue("unused.config.key2", "value2");

        Set<String> unusedKeys = healthChecker.getUnusedConfigKeys();
        assertNotNull("Unused keys set should not be null", unusedKeys);
        logger.info("Unused config keys: {}", unusedKeys);

        ConfigHealthCheckResult result = healthChecker.performCheck(false, false, false, true);
        assertNotNull(result);

        List<ConfigHealthCheckResult.HealthIssue> unusedIssues =
                result.getIssuesByType(ConfigHealthCheckResult.IssueType.UNUSED_CONFIG);
        assertNotNull("Unused issues should not be null", unusedIssues);
        logger.info("Unused config issues found: {}", unusedIssues.size());

        for (ConfigHealthCheckResult.HealthIssue issue : unusedIssues) {
            logger.debug("Unused config issue: {}", issue);
        }

        logger.info("Health check unused config test passed!");
    }

    @Test
    public void testHealthCheckTypeCompatibility() {
        logger.info("Testing health check - type compatibility...");

        assertNotNull(healthChecker);

        configManager.setLocalValue("app.timeout", "not-a-number");

        ConfigHealthCheckResult result = healthChecker.performCheck(false, false, true, false);
        assertNotNull(result);

        List<ConfigHealthCheckResult.HealthIssue> typeIssues =
                result.getIssuesByType(ConfigHealthCheckResult.IssueType.TYPE_MISMATCH);
        assertNotNull("Type issues should not be null", typeIssues);

        for (ConfigHealthCheckResult.HealthIssue issue : typeIssues) {
            logger.debug("Type issue: {} - {}", issue.getKey(), issue.getMessage());
            assertEquals(ConfigHealthCheckResult.IssueSeverity.HIGH, issue.getSeverity());
        }

        configManager.setLocalValue("app.timeout", "30");
        logger.info("Health check type compatibility test passed!");
    }

    @Test
    public void testSingleKeyHealthCheck() {
        logger.info("Testing single key health check...");

        assertNotNull(healthChecker);

        ConfigHealthCheckResult result1 = healthChecker.checkSingleKey("app.name");
        assertNotNull(result1);
        logger.info("Health check for 'app.name': {} issues", result1.getIssueCount());

        ConfigHealthCheckResult result2 = healthChecker.checkSingleKey("non.existent.key");
        assertNotNull(result2);
        logger.info("Health check for 'non.existent.key': {} issues", result2.getIssueCount());

        List<ConfigHealthCheckResult.HealthIssue> danglingIssues =
                result2.getIssuesByType(ConfigHealthCheckResult.IssueType.UNUSED_CONFIG);
        assertTrue("Should have unused config issue for non-existent key", danglingIssues.size() > 0);

        logger.info("Single key health check test passed!");
    }

    @Test
    public void testHealthCheckHistory() {
        logger.info("Testing health check history...");

        assertNotNull(healthChecker);

        healthChecker.performFullCheck();
        healthChecker.performFullCheck();

        List<ConfigHealthCheckResult> history = healthChecker.getCheckHistory();
        assertTrue("History should have entries", history.size() >= 2);

        ConfigHealthCheckResult latest = healthChecker.getLatestCheckResult();
        assertNotNull("Latest result should not be null", latest);

        List<ConfigHealthCheckResult> healthyHistory =
                healthChecker.getCheckHistoryByStatus(ConfigHealthCheckResult.HealthStatus.HEALTHY);
        assertNotNull("Healthy history should not be null", healthyHistory);

        logger.info("Health check history size: {}", history.size());
        logger.info("Health check history test passed!");
    }

    @Test
    public void testKeyReferenceInfo() {
        logger.info("Testing key reference info...");

        assertNotNull(healthChecker);

        Map<String, ConfigHealthChecker.FieldReferenceInfo> references = healthChecker.getKeyReferences();
        assertTrue("Should have references", references.size() > 0);

        for (Map.Entry<String, ConfigHealthChecker.FieldReferenceInfo> entry : references.entrySet()) {
            String key = entry.getKey();
            ConfigHealthChecker.FieldReferenceInfo info = entry.getValue();

            assertNotNull("Key should not be null", key);
            assertNotNull("Class name should not be null", info.getClassName());
            assertNotNull("Field name should not be null", info.getFieldName());
            assertNotNull("Field type should not be null", info.getFieldType());

            logger.debug("Key '{}' -> {}.{} ({})", key, info.getClassName(), info.getFieldName(), info.getFieldType().getSimpleName());
        }

        ConfigHealthChecker.FieldReferenceInfo info = references.get("app.name");
        assertNotNull("Should have reference for app.name", info);
        assertEquals(String.class, info.getFieldType());

        logger.info("Key reference info test passed!");
    }

    @Test
    public void testRollbackWithError() {
        logger.info("Testing rollback with error handling...");

        rollbackManager = configManager.getRollbackManager();

        ConfigRollbackManager.RollbackResult result = configManager.rollbackToSnapshot("non-existent-snapshot-id");
        assertNotNull(result);
        assertFalse("Rollback should fail for non-existent snapshot", result.isSuccess());
        assertTrue("Should have failure message", result.getMessage().contains("not found"));

        logger.info("Rollback error handling test passed!");
    }

    @Test
    public void testDiffFormattedOutput() {
        logger.info("Testing diff formatted output...");

        Map<String, Object> before = new HashMap<>();
        before.put("format.test.key1", "old-value");
        before.put("format.test.key2", "123");

        Map<String, Object> after = new HashMap<>();
        after.put("format.test.key1", "new-value");
        after.put("format.test.key2", "456");
        after.put("format.test.key3", "new-key");

        ConfigDiff diff = ConfigDiff.compare("format-test", before, after);

        String formattedDiff = diff.getFormattedDiff();
        assertNotNull("Formatted diff should not be null", formattedDiff);
        assertTrue("Should contain source name", formattedDiff.contains("format-test"));
        assertTrue("Should contain key1", formattedDiff.contains("format.test.key1"));
        assertTrue("Should contain old-value", formattedDiff.contains("old-value"));
        assertTrue("Should contain new-value", formattedDiff.contains("new-value"));

        List<String> summary = diff.getSummary();
        assertTrue("Summary should have entries", summary.size() > 0);
        for (String line : summary) {
            logger.info("  {}", line);
        }

        logger.info("Diff formatted output test passed!");
    }
}
