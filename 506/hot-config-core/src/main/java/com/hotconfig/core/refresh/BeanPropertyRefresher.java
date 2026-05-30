package com.hotconfig.core.refresh;

import com.hotconfig.annotation.HotConfig;
import com.hotconfig.annotation.HotValue;
import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.event.ConfigChangeEvent;
import com.hotconfig.core.listener.ConfigChangeListener;
import com.hotconfig.core.proxy.DynamicProxyFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;
import java.lang.reflect.Type;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

public class BeanPropertyRefresher implements ConfigChangeListener {

    private static final Logger logger = LoggerFactory.getLogger(BeanPropertyRefresher.class);

    private final ConfigManager configManager;

    private final DynamicProxyFactory proxyFactory;

    private final Map<Class<?>, List<Object>> hotConfigBeans = new ConcurrentHashMap<>();

    private final Map<Object, Class<?>> beanTypeMap = new IdentityHashMap<>();

    private final Queue<Runnable> deferredRefreshQueue = new LinkedList<>();

    private final AtomicBoolean refreshing = new AtomicBoolean(false);

    private volatile boolean deferMode = false;

    private final ThreadLocal<Set<Object>> refreshInProgress = ThreadLocal.withInitial(HashSet::new);

    public BeanPropertyRefresher() {
        this(ConfigManager.getInstance(), DynamicProxyFactory.getInstance());
    }

    public BeanPropertyRefresher(ConfigManager configManager, DynamicProxyFactory proxyFactory) {
        this.configManager = configManager;
        this.proxyFactory = proxyFactory;
        this.configManager.addGlobalListener(this);
    }

    public void setDeferMode(boolean deferMode) {
        this.deferMode = deferMode;
        if (!deferMode) {
            flushDeferredRefresh();
        }
    }

    public boolean isDeferMode() {
        return deferMode;
    }

    public synchronized void flushDeferredRefresh() {
        if (deferredRefreshQueue.isEmpty()) {
            return;
        }

        logger.info("Flushing {} deferred refresh tasks", deferredRefreshQueue.size());

        List<Runnable> tasks = new ArrayList<>(deferredRefreshQueue);
        deferredRefreshQueue.clear();

        for (Runnable task : tasks) {
            try {
                task.run();
            } catch (Exception e) {
                logger.error("Failed to execute deferred refresh task", e);
            }
        }

        logger.info("Deferred refresh tasks completed");
    }

    public void registerBean(Object bean) {
        if (bean == null) {
            return;
        }

        Class<?> beanClass = bean.getClass();
        HotConfig hotConfig = findHotConfigAnnotation(beanClass);

        if (hotConfig == null) {
            logger.debug("Bean {} is not annotated with @HotConfig, skipping", beanClass.getName());
            return;
        }

        Class<?> targetType = getTargetType(bean);
        beanTypeMap.put(bean, targetType);
        hotConfigBeans.computeIfAbsent(targetType, k -> new ArrayList<>()).add(bean);

        logger.info("Registered hot config bean: {}", targetType.getName());

        if (deferMode) {
            logger.debug("Deferring initial refresh for bean: {}", targetType.getName());
            deferredRefreshQueue.add(() -> initialRefreshBean(bean, targetType, hotConfig));
        } else {
            initialRefreshBean(bean, targetType, hotConfig);
        }
    }

    private void initialRefreshBean(Object bean, Class<?> targetType, HotConfig hotConfig) {
        String prefix = hotConfig.prefix();
        try {
            Field[] fields = getAllFields(targetType);
            for (Field field : fields) {
                HotValue hotValue = field.getAnnotation(HotValue.class);
                if (hotValue == null) {
                    continue;
                }

                String configKey = hotValue.value();
                String fullKey = prefix.isEmpty() ? configKey : prefix + "." + configKey;

                Type fieldType = TypeConverter.resolveGenericType(field);
                Object value = configManager.getValue(fullKey, fieldType, hotValue.defaultValue());

                if (hotValue.required() && value == null) {
                    throw new IllegalArgumentException("Required config key '" + fullKey + "' is not set");
                }

                field.setAccessible(true);
                Object oldValue = field.get(bean);

                if (!Objects.equals(oldValue, value)) {
                    field.set(bean, value);
                    logger.debug("Initialized field {}.{} with value: {}",
                            targetType.getSimpleName(), field.getName(), value);
                }
            }
        } catch (Exception e) {
            logger.error("Failed to initialize bean properties for: " + targetType.getName(), e);
        }
    }

    public void unregisterBean(Object bean) {
        if (bean == null) {
            return;
        }

        Class<?> targetType = beanTypeMap.remove(bean);
        if (targetType != null) {
            List<Object> beans = hotConfigBeans.get(targetType);
            if (beans != null) {
                beans.remove(bean);
                if (beans.isEmpty()) {
                    hotConfigBeans.remove(targetType);
                }
            }
        }
    }

    public void refreshBean(Object bean) {
        if (bean == null) {
            return;
        }

        Set<Object> inProgress = refreshInProgress.get();
        if (inProgress.contains(bean)) {
            logger.debug("Circular refresh detected for bean {}, deferring refresh", bean.getClass().getName());
            deferredRefreshQueue.add(() -> doRefreshBean(bean));
            return;
        }

        try {
            inProgress.add(bean);
            doRefreshBean(bean);
        } finally {
            inProgress.remove(bean);
        }
    }

    private void doRefreshBean(Object bean) {
        Class<?> targetType = beanTypeMap.get(bean);
        if (targetType == null) {
            targetType = getTargetType(bean);
        }

        HotConfig hotConfig = findHotConfigAnnotation(targetType);
        if (hotConfig == null) {
            return;
        }

        String prefix = hotConfig.prefix();
        refreshBeanProperties(bean, targetType, prefix);
    }

    public void refreshAllBeans() {
        if (refreshing.compareAndSet(false, true)) {
            try {
                for (Map.Entry<Class<?>, List<Object>> entry : hotConfigBeans.entrySet()) {
                    Class<?> targetType = entry.getKey();
                    HotConfig hotConfig = targetType.getAnnotation(HotConfig.class);
                    if (hotConfig == null) {
                        continue;
                    }

                    String prefix = hotConfig.prefix();
                    for (Object bean : entry.getValue()) {
                        refreshBean(bean);
                    }
                }
                flushDeferredRefresh();
                logger.info("Refreshed {} hot config beans", hotConfigBeans.size());
            } finally {
                refreshing.set(false);
            }
        } else {
            logger.debug("Refresh already in progress, skipping refreshAllBeans");
        }
    }

    public void refreshBeansByPrefix(String prefix) {
        for (Map.Entry<Class<?>, List<Object>> entry : hotConfigBeans.entrySet()) {
            Class<?> targetType = entry.getKey();
            HotConfig hotConfig = targetType.getAnnotation(HotConfig.class);
            if (hotConfig == null) {
                continue;
            }

            String beanPrefix = hotConfig.prefix();
            if (beanPrefix.startsWith(prefix) || prefix.startsWith(beanPrefix)) {
                for (Object bean : entry.getValue()) {
                    refreshBean(bean);
                }
            }
        }
    }

    public void refreshBeansByKey(String key) {
        for (Map.Entry<Class<?>, List<Object>> entry : hotConfigBeans.entrySet()) {
            Class<?> targetType = entry.getKey();
            HotConfig hotConfig = targetType.getAnnotation(HotConfig.class);
            if (hotConfig == null) {
                continue;
            }

            String prefix = hotConfig.prefix();
            if (key.startsWith(prefix)) {
                for (Object bean : entry.getValue()) {
                    if (isKeyRelevant(bean, targetType, key, prefix)) {
                        refreshBean(bean);
                    }
                }
            }
        }
    }

    private void refreshBeanProperties(Object bean, Class<?> targetType, String prefix) {
        try {
            Field[] fields = getAllFields(targetType);
            for (Field field : fields) {
                HotValue hotValue = field.getAnnotation(HotValue.class);
                if (hotValue == null) {
                    continue;
                }

                String configKey = hotValue.value();
                String fullKey = prefix.isEmpty() ? configKey : prefix + "." + configKey;

                Type fieldType = TypeConverter.resolveGenericType(field);
                Object value = configManager.getValue(fullKey, fieldType, hotValue.defaultValue());

                field.setAccessible(true);
                Object oldValue = field.get(bean);

                if (!Objects.equals(oldValue, value)) {
                    field.set(bean, value);
                    logger.debug("Updated field {}.{} from {} to {}",
                            targetType.getSimpleName(), field.getName(), oldValue, value);
                }
            }
        } catch (Exception e) {
            logger.error("Failed to refresh bean properties for: " + targetType.getName(), e);
        }
    }

    private boolean isKeyRelevant(Object bean, Class<?> targetType, String key, String prefix) {
        Field[] fields = getAllFields(targetType);
        for (Field field : fields) {
            HotValue hotValue = field.getAnnotation(HotValue.class);
            if (hotValue == null) {
                continue;
            }

            String configKey = hotValue.value();
            String fullKey = prefix.isEmpty() ? configKey : prefix + "." + configKey;

            if (key.equals(fullKey)) {
                return true;
            }
        }
        return false;
    }

    private Class<?> getTargetType(Object bean) {
        if (Proxy.isProxyClass(bean.getClass())) {
            InvocationHandler handler = Proxy.getInvocationHandler(bean);
            try {
                Field targetField = handler.getClass().getDeclaredField("target");
                targetField.setAccessible(true);
                Object target = targetField.get(handler);
                return target.getClass();
            } catch (Exception e) {
                return bean.getClass().getInterfaces()[0];
            }
        }

        String className = bean.getClass().getName();
        if (className.contains("$$")) {
            return bean.getClass().getSuperclass();
        }

        return bean.getClass();
    }

    private HotConfig findHotConfigAnnotation(Class<?> clazz) {
        Class<?> current = clazz;
        while (current != null && current != Object.class) {
            HotConfig annotation = current.getAnnotation(HotConfig.class);
            if (annotation != null) {
                return annotation;
            }
            for (Class<?> iface : current.getInterfaces()) {
                annotation = iface.getAnnotation(HotConfig.class);
                if (annotation != null) {
                    return annotation;
                }
            }
            current = current.getSuperclass();
        }
        return null;
    }

    private Field[] getAllFields(Class<?> clazz) {
        List<Field> fields = new ArrayList<>();
        Class<?> current = clazz;
        while (current != null && current != Object.class) {
            fields.addAll(Arrays.asList(current.getDeclaredFields()));
            current = current.getSuperclass();
        }
        return fields.toArray(new Field[0]);
    }

    @Override
    public void onChange(ConfigChangeEvent event) {
        logger.debug("Received config change event, refreshing relevant beans...");

        if (deferMode) {
            logger.debug("Defer mode enabled, deferring refresh for changed keys: {}", event.getChangedKeys());
            deferredRefreshQueue.add(() -> {
                for (String changedKey : event.getChangedKeys()) {
                    refreshBeansByKey(changedKey);
                }
                proxyFactory.refreshAllProxies();
            });
            return;
        }

        if (refreshing.compareAndSet(false, true)) {
            try {
                for (String changedKey : event.getChangedKeys()) {
                    refreshBeansByKey(changedKey);
                }
                flushDeferredRefresh();
                proxyFactory.refreshAllProxies();
            } finally {
                refreshing.set(false);
            }
        } else {
            logger.debug("Refresh already in progress, deferring refresh for changed keys: {}", event.getChangedKeys());
            deferredRefreshQueue.add(() -> {
                for (String changedKey : event.getChangedKeys()) {
                    refreshBeansByKey(changedKey);
                }
                proxyFactory.refreshAllProxies();
            });
        }
    }

    public Set<Class<?>> getRegisteredBeanTypes() {
        return hotConfigBeans.keySet();
    }

    public List<Object> getBeansByType(Class<?> type) {
        return hotConfigBeans.getOrDefault(type, Collections.emptyList());
    }
}
