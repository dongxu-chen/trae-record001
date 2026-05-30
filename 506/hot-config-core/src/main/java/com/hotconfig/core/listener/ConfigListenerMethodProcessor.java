package com.hotconfig.core.listener;

import com.hotconfig.annotation.ConfigListener;
import com.hotconfig.annotation.DependsOnConfig;
import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.event.ConfigChangeEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Method;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

public class ConfigListenerMethodProcessor {

    private static final Logger logger = LoggerFactory.getLogger(ConfigListenerMethodProcessor.class);

    private final ConfigManager configManager;

    private final Map<Object, List<ListenerMethod>> listenerMethods = new IdentityHashMap<>();

    private final List<ListenerMethod> orderedListeners = new ArrayList<>();

    private final Map<String, List<ListenerMethod>> listenersByKey = new ConcurrentHashMap<>();

    private ExecutorService asyncExecutor;

    public ConfigListenerMethodProcessor() {
        this(ConfigManager.getInstance());
    }

    public ConfigListenerMethodProcessor(ConfigManager configManager) {
        this.configManager = configManager;
        initAsyncExecutor();
    }

    private void initAsyncExecutor() {
        this.asyncExecutor = Executors.newFixedThreadPool(2, new ThreadFactory() {
            private final AtomicInteger counter = new AtomicInteger(0);

            @Override
            public Thread newThread(Runnable r) {
                Thread thread = new Thread(r, "hot-config-listener-" + counter.incrementAndGet());
                thread.setDaemon(true);
                return thread;
            }
        });
    }

    public void processBean(Object bean) {
        if (bean == null) {
            return;
        }

        Class<?> beanClass = bean.getClass();
        Method[] methods = getAllMethods(beanClass);

        for (Method method : methods) {
            ConfigListener annotation = method.getAnnotation(ConfigListener.class);
            if (annotation == null) {
                continue;
            }

            if (!isValidListenerMethod(method)) {
                logger.warn("Method {} in class {} is not a valid @ConfigListener method. " +
                        "It must have exactly one parameter of type ConfigChangeEvent",
                        method.getName(), beanClass.getName());
                continue;
            }

            DependsOnConfig dependsOnConfig = method.getAnnotation(DependsOnConfig.class);
            ListenerMethod listenerMethod = new ListenerMethod(bean, method, annotation, dependsOnConfig);
            listenerMethods.computeIfAbsent(bean, k -> new ArrayList<>()).add(listenerMethod);
            addOrderedListener(listenerMethod);

            ConfigChangeListener adapter = createListenerAdapter(listenerMethod);
            configManager.addGlobalListener(adapter);

            logger.info("Registered @ConfigListener method: {}.{} with order: {}",
                    beanClass.getName(), method.getName(), listenerMethod.getOrder());
        }
    }

    private void addOrderedListener(ListenerMethod listenerMethod) {
        synchronized (orderedListeners) {
            orderedListeners.add(listenerMethod);
            orderedListeners.sort(Comparator.comparingInt(ListenerMethod::getOrder));
        }

        String[] keys = listenerMethod.getKeys();
        String[] prefixes = listenerMethod.getPrefixes();

        if (keys != null && keys.length > 0) {
            for (String key : keys) {
                listenersByKey.computeIfAbsent(key, k -> new ArrayList<>()).add(listenerMethod);
            }
        }

        if (prefixes != null && prefixes.length > 0) {
            for (String prefix : prefixes) {
                listenersByKey.computeIfAbsent(prefix, k -> new ArrayList<>()).add(listenerMethod);
            }
        }
    }

    public void unprocessBean(Object bean) {
        if (bean == null) {
            return;
        }
        listenerMethods.remove(bean);
    }

    private ConfigChangeListener createListenerAdapter(ListenerMethod listenerMethod) {
        return new ConfigChangeListener() {
            @Override
            public void onChange(ConfigChangeEvent event) {
                if (!support(event)) {
                    return;
                }

                if (!checkDependencies(listenerMethod, event)) {
                    logger.debug("Dependencies not satisfied for listener method: {}, skipping",
                            listenerMethod.getMethod().getName());
                    return;
                }

                Runnable invocation = () -> {
                    try {
                        listenerMethod.invoke(event);
                    } catch (Exception e) {
                        logger.error("Failed to invoke @ConfigListener method: {}",
                                listenerMethod.getMethod().getName(), e);
                    }
                };

                if (listenerMethod.isAsync()) {
                    asyncExecutor.submit(invocation);
                } else {
                    invocation.run();
                }
            }

            @Override
            public boolean support(ConfigChangeEvent event) {
                String[] keys = listenerMethod.getKeys();
                String[] prefixes = listenerMethod.getPrefixes();
                String[] sources = listenerMethod.getSources();

                if (sources != null && sources.length > 0) {
                    boolean sourceMatch = false;
                    for (String source : sources) {
                        if (event.getSourceName().equals(source) || event.getSourceName().startsWith(source + ":")) {
                            sourceMatch = true;
                            break;
                        }
                    }
                    if (!sourceMatch) {
                        return false;
                    }
                }

                if (keys != null && keys.length > 0) {
                    for (String key : keys) {
                        if (event.isKeyChanged(key)) {
                            return true;
                        }
                    }
                    return false;
                }

                if (prefixes != null && prefixes.length > 0) {
                    for (String prefix : prefixes) {
                        if (event.isPrefixChanged(prefix)) {
                            return true;
                        }
                    }
                    return false;
                }

                return true;
            }

            private boolean checkDependencies(ListenerMethod listenerMethod, ConfigChangeEvent event) {
                String[] dependsOn = listenerMethod.getDependsOn();
                if (dependsOn == null || dependsOn.length == 0) {
                    return true;
                }

                for (String dependency : dependsOn) {
                    if (!configManager.containsKey(dependency) && !event.isKeyChanged(dependency)) {
                        logger.debug("Dependency key '{}' not found for listener: {}",
                                dependency, listenerMethod.getMethod().getName());
                        return false;
                    }
                }
                return true;
            }
        };
    }

    public List<ListenerMethod> getOrderedListeners() {
        synchronized (orderedListeners) {
            return new ArrayList<>(orderedListeners);
        }
    }

    public List<ListenerMethod> getListenersForKey(String key) {
        return listenersByKey.getOrDefault(key, Collections.emptyList());
    }

    public void invokeOrderedListeners(ConfigChangeEvent event) {
        List<ListenerMethod> listeners = getOrderedListeners();
        logger.debug("Invoking {} ordered listeners for event: {}", listeners.size(), event.getChangedKeys());

        for (ListenerMethod listener : listeners) {
            try {
                if (listener.support(event) && checkDependencies(listener, event)) {
                    if (listener.isAsync()) {
                        asyncExecutor.submit(() -> {
                            try {
                                listener.invoke(event);
                            } catch (Exception e) {
                                logger.error("Failed to invoke ordered listener: {}",
                                        listener.getMethod().getName(), e);
                            }
                        });
                    } else {
                        listener.invoke(event);
                    }
                }
            } catch (Exception e) {
                logger.error("Failed to invoke ordered listener: {}", listener.getMethod().getName(), e);
            }
        }
    }

    private boolean checkDependencies(ListenerMethod listenerMethod, ConfigChangeEvent event) {
        String[] dependsOn = listenerMethod.getDependsOn();
        if (dependsOn == null || dependsOn.length == 0) {
            return true;
        }

        for (String dependency : dependsOn) {
            if (!configManager.containsKey(dependency) && !event.isKeyChanged(dependency)) {
                return false;
            }
        }
        return true;
    }

    private boolean isValidListenerMethod(Method method) {
        Class<?>[] parameterTypes = method.getParameterTypes();
        return parameterTypes.length == 1 && parameterTypes[0] == ConfigChangeEvent.class;
    }

    private Method[] getAllMethods(Class<?> clazz) {
        List<Method> methods = new ArrayList<>();
        Class<?> current = clazz;
        while (current != null && current != Object.class) {
            methods.addAll(Arrays.asList(current.getDeclaredMethods()));
            for (Class<?> iface : current.getInterfaces()) {
                methods.addAll(Arrays.asList(iface.getDeclaredMethods()));
            }
            current = current.getSuperclass();
        }
        return methods.toArray(new Method[0]);
    }

    public void destroy() {
        if (asyncExecutor != null && !asyncExecutor.isShutdown()) {
            asyncExecutor.shutdown();
        }
        listenerMethods.clear();
    }

    public Set<Object> getRegisteredBeans() {
        return listenerMethods.keySet();
    }

    public List<ListenerMethod> getListenerMethods(Object bean) {
        return listenerMethods.getOrDefault(bean, Collections.emptyList());
    }

    public static class ListenerMethod {
        private final Object bean;
        private final Method method;
        private final ConfigListener annotation;
        private final DependsOnConfig dependsOnConfig;
        private final int order;
        private final String[] dependsOn;

        public ListenerMethod(Object bean, Method method, ConfigListener annotation, DependsOnConfig dependsOnConfig) {
            this.bean = bean;
            this.method = method;
            this.annotation = annotation;
            this.dependsOnConfig = dependsOnConfig;
            this.method.setAccessible(true);

            if (dependsOnConfig != null) {
                this.order = dependsOnConfig.order();
                this.dependsOn = dependsOnConfig.value();
            } else {
                this.order = 0;
                this.dependsOn = new String[0];
            }
        }

        public void invoke(ConfigChangeEvent event) throws Exception {
            method.invoke(bean, event);
        }

        public boolean support(ConfigChangeEvent event) {
            String[] keys = getKeys();
            String[] prefixes = getPrefixes();
            String[] sources = getSources();

            if (sources != null && sources.length > 0) {
                boolean sourceMatch = false;
                for (String source : sources) {
                    if (event.getSourceName().equals(source) || event.getSourceName().startsWith(source + ":")) {
                        sourceMatch = true;
                        break;
                    }
                }
                if (!sourceMatch) {
                    return false;
                }
            }

            if (keys != null && keys.length > 0) {
                for (String key : keys) {
                    if (event.isKeyChanged(key)) {
                        return true;
                    }
                }
                return false;
            }

            if (prefixes != null && prefixes.length > 0) {
                for (String prefix : prefixes) {
                    if (event.isPrefixChanged(prefix)) {
                        return true;
                    }
                }
                return false;
            }

            return true;
        }

        public Object getBean() {
            return bean;
        }

        public Method getMethod() {
            return method;
        }

        public int getOrder() {
            return order;
        }

        public String[] getDependsOn() {
            return dependsOn;
        }

        public String[] getKeys() {
            return annotation.keys();
        }

        public String[] getPrefixes() {
            return annotation.prefixes();
        }

        public String[] getSources() {
            return annotation.sources();
        }

        public boolean isAsync() {
            return annotation.async();
        }
    }
}
