package com.hotconfig.core.proxy;

import com.hotconfig.annotation.HotConfig;
import com.hotconfig.annotation.HotValue;
import com.hotconfig.core.ConfigManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.concurrent.ConcurrentHashMap;

public class DynamicProxyFactory {

    private static final Logger logger = LoggerFactory.getLogger(DynamicProxyFactory.class);

    private static final DynamicProxyFactory INSTANCE = new DynamicProxyFactory();

    private final ConcurrentHashMap<Class<?>, Object> proxyCache = new ConcurrentHashMap<>();

    private final ConfigManager configManager;

    private DynamicProxyFactory() {
        this.configManager = ConfigManager.getInstance();
    }

    public static DynamicProxyFactory getInstance() {
        return INSTANCE;
    }

    @SuppressWarnings("unchecked")
    public <T> T createProxy(Class<T> targetClass) {
        if (!targetClass.isAnnotationPresent(HotConfig.class)) {
            logger.warn("Class {} is not annotated with @HotConfig, returning null", targetClass.getName());
            return null;
        }

        T proxy = (T) proxyCache.get(targetClass);
        if (proxy != null) {
            return proxy;
        }

        synchronized (targetClass) {
            proxy = (T) proxyCache.get(targetClass);
            if (proxy != null) {
                return proxy;
            }

            HotConfig hotConfig = targetClass.getAnnotation(HotConfig.class);
            String prefix = hotConfig.prefix();

            if (targetClass.isInterface()) {
                proxy = createJdkProxy(targetClass, prefix);
            } else {
                proxy = createCglibProxy(targetClass, prefix);
            }

            if (proxy != null) {
                proxyCache.put(targetClass, proxy);
                logger.info("Created dynamic proxy for class: {}", targetClass.getName());
            }

            return proxy;
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T createJdkProxy(Class<T> targetClass, String prefix) {
        try {
            T targetInstance = createTargetInstance(targetClass);
            InvocationHandler handler = new HotConfigInvocationHandler(targetInstance, prefix, configManager);
            return (T) Proxy.newProxyInstance(
                    targetClass.getClassLoader(),
                    new Class<?>[]{targetClass},
                    handler
            );
        } catch (Exception e) {
            logger.error("Failed to create JDK proxy for class: " + targetClass.getName(), e);
            return null;
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T createCglibProxy(Class<T> targetClass, String prefix) {
        try {
            Class<?> cglibEnhancerClass = Class.forName("org.springframework.cglib.proxy.Enhancer");
            Class<?> cglibCallbackClass = Class.forName("org.springframework.cglib.proxy.Callback");
            Class<?> cglibMethodInterceptorClass = Class.forName("org.springframework.cglib.proxy.MethodInterceptor");

            Object enhancer = cglibEnhancerClass.getDeclaredConstructor().newInstance();

            cglibEnhancerClass.getMethod("setSuperclass", Class.class).invoke(enhancer, targetClass);

            T targetInstance = createTargetInstance(targetClass);
            Object interceptor = createCglibInterceptor(targetInstance, prefix, configManager);

            cglibEnhancerClass.getMethod("setCallback", cglibCallbackClass).invoke(enhancer, interceptor);

            return (T) cglibEnhancerClass.getMethod("create").invoke(enhancer);
        } catch (ClassNotFoundException e) {
            logger.warn("CGLIB not available, falling back to reflection-based proxy for class: {}", targetClass.getName());
            return createReflectionProxy(targetClass, prefix);
        } catch (Exception e) {
            logger.error("Failed to create CGLIB proxy for class: " + targetClass.getName(), e);
            return createReflectionProxy(targetClass, prefix);
        }
    }

    private Object createCglibInterceptor(Object target, String prefix, ConfigManager configManager) throws Exception {
        return Proxy.newProxyInstance(
                Thread.currentThread().getContextClassLoader(),
                new Class<?>[]{Class.forName("org.springframework.cglib.proxy.MethodInterceptor")},
                (proxy, method, args) -> {
                    if ("intercept".equals(method.getName())) {
                        Object obj = args[0];
                        Method realMethod = (Method) args[1];
                        Object[] arguments = (Object[]) args[2];
                        return interceptMethod(target, prefix, configManager, realMethod, arguments);
                    }
                    return method.invoke(this, args);
                }
        );
    }

    @SuppressWarnings("unchecked")
    private <T> T createReflectionProxy(Class<T> targetClass, String prefix) {
        try {
            T instance = createTargetInstance(targetClass);
            initializeHotValues(instance, prefix);
            return instance;
        } catch (Exception e) {
            logger.error("Failed to create reflection proxy for class: " + targetClass.getName(), e);
            return null;
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T createTargetInstance(Class<T> targetClass) throws Exception {
        try {
            return targetClass.getDeclaredConstructor().newInstance();
        } catch (NoSuchMethodException e) {
            logger.warn("No default constructor found for class: {}, using sun.misc.Unsafe", targetClass.getName());
            Class<?> unsafeClass = Class.forName("sun.misc.Unsafe");
            Field theUnsafe = unsafeClass.getDeclaredField("theUnsafe");
            theUnsafe.setAccessible(true);
            Object unsafe = theUnsafe.get(null);
            return (T) unsafeClass.getMethod("allocateInstance", Class.class).invoke(unsafe, targetClass);
        }
    }

    private Object interceptMethod(Object target, String prefix, ConfigManager configManager,
                                    Method method, Object[] args) throws Throwable {
        String methodName = method.getName();

        if (methodName.startsWith("get") && methodName.length() > 3 && args == null) {
            String fieldName = decapitalize(methodName.substring(3));
            Field field = findField(target.getClass(), fieldName);

            if (field != null && field.isAnnotationPresent(HotValue.class)) {
                HotValue hotValue = field.getAnnotation(HotValue.class);
                String configKey = hotValue.value();
                String fullKey = prefix.isEmpty() ? configKey : prefix + "." + configKey;

                Object value = configManager.getValue(fullKey, field.getType(), hotValue.defaultValue());
                if (value != null) {
                    return value;
                }
            }
        }

        return method.invoke(target, args);
    }

    private void initializeHotValues(Object instance, String prefix) throws IllegalAccessException {
        Field[] fields = instance.getClass().getDeclaredFields();
        for (Field field : fields) {
            if (field.isAnnotationPresent(HotValue.class)) {
                HotValue hotValue = field.getAnnotation(HotValue.class);
                String configKey = hotValue.value();
                String fullKey = prefix.isEmpty() ? configKey : prefix + "." + configKey;

                Object value = configManager.getValue(fullKey, field.getType(), hotValue.defaultValue());

                field.setAccessible(true);
                field.set(instance, value);

                logger.debug("Initialized field {}.{} with value: {}",
                        instance.getClass().getSimpleName(), field.getName(), value);
            }
        }
    }

    private Field findField(Class<?> clazz, String fieldName) {
        Class<?> current = clazz;
        while (current != null && current != Object.class) {
            try {
                return current.getDeclaredField(fieldName);
            } catch (NoSuchFieldException e) {
                current = current.getSuperclass();
            }
        }
        return null;
    }

    private String decapitalize(String str) {
        if (str == null || str.isEmpty()) {
            return str;
        }
        if (str.length() == 1 || !Character.isUpperCase(str.charAt(1))) {
            return Character.toLowerCase(str.charAt(0)) + str.substring(1);
        }
        return str;
    }

    public void refreshProxy(Class<?> targetClass) {
        proxyCache.remove(targetClass);
        logger.debug("Cleared proxy cache for class: {}", targetClass.getName());
    }

    public void refreshAllProxies() {
        proxyCache.clear();
        logger.debug("Cleared all proxy caches");
    }
}
