package com.hotconfig.spring;

import com.hotconfig.annotation.HotConfig;
import com.hotconfig.annotation.HotValue;
import com.hotconfig.core.ConfigManager;
import com.hotconfig.core.convert.TypeConverter;
import com.hotconfig.core.health.ConfigHealthChecker;
import com.hotconfig.core.listener.ConfigListenerMethodProcessor;
import com.hotconfig.core.proxy.DynamicProxyFactory;
import com.hotconfig.core.refresh.BeanPropertyRefresher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.BeansException;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.core.PriorityOrdered;

import java.lang.reflect.Field;
import java.lang.reflect.Type;
import java.util.Arrays;

public class HotConfigBeanPostProcessor implements BeanPostProcessor, ApplicationContextAware, PriorityOrdered {

    private static final Logger logger = LoggerFactory.getLogger(HotConfigBeanPostProcessor.class);

    private final ConfigManager configManager;
    private final DynamicProxyFactory proxyFactory;
    private final BeanPropertyRefresher propertyRefresher;
    private final ConfigListenerMethodProcessor listenerProcessor;
    private final ConfigHealthChecker healthChecker;

    private ApplicationContext applicationContext;

    public HotConfigBeanPostProcessor(ConfigManager configManager,
                                       DynamicProxyFactory proxyFactory,
                                       BeanPropertyRefresher propertyRefresher,
                                       ConfigListenerMethodProcessor listenerProcessor) {
        this.configManager = configManager;
        this.proxyFactory = proxyFactory;
        this.propertyRefresher = propertyRefresher;
        this.listenerProcessor = listenerProcessor;
        this.healthChecker = ConfigHealthChecker.getInstance(configManager);
    }

    @Override
    public Object postProcessBeforeInitialization(Object bean, String beanName) throws BeansException {
        if (bean == null) {
            return bean;
        }

        Class<?> beanClass = bean.getClass();

        listenerProcessor.processBean(bean);

        HotConfig hotConfig = findHotConfigAnnotation(beanClass);
        if (hotConfig != null) {
            logger.debug("Processing @HotConfig bean: {}", beanName);
            processHotConfigBean(bean, beanName, hotConfig);
        }

        processHotValueFields(bean, beanClass);

        return bean;
    }

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) throws BeansException {
        if (bean == null) {
            return bean;
        }

        Class<?> beanClass = bean.getClass();
        HotConfig hotConfig = findHotConfigAnnotation(beanClass);

        if (hotConfig != null && hotConfig.autoRefresh()) {
            propertyRefresher.registerBean(bean);
            logger.info("Registered hot config bean for auto refresh: {}", beanName);
        }

        if (hotConfig != null) {
            healthChecker.registerConfigBean(bean, beanClass);
            logger.debug("Registered config bean for health check: {}", beanName);
        }

        return bean;
    }

    private void processHotConfigBean(Object bean, String beanName, HotConfig hotConfig) {
        try {
            initializeHotConfigFields(bean, hotConfig);
        } catch (Exception e) {
            logger.error("Failed to process @HotConfig bean: " + beanName, e);
        }
    }

    private void initializeHotConfigFields(Object bean, HotConfig hotConfig) throws IllegalAccessException {
        String prefix = hotConfig.prefix();
        Field[] fields = getAllFields(bean.getClass());

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
            field.set(bean, value);

            logger.debug("Initialized field {}.{} with value: {}",
                    bean.getClass().getSimpleName(), field.getName(), value);
        }
    }

    private void processHotValueFields(Object bean, Class<?> beanClass) {
        if (beanClass.isAnnotationPresent(HotConfig.class)) {
            return;
        }

        Field[] fields = getAllFields(beanClass);
        for (Field field : fields) {
            HotValue hotValue = field.getAnnotation(HotValue.class);
            if (hotValue == null) {
                continue;
            }

            try {
                Type fieldType = TypeConverter.resolveGenericType(field);
                Object value = configManager.getValue(hotValue.value(), fieldType, hotValue.defaultValue());

                if (hotValue.required() && value == null) {
                    throw new IllegalArgumentException("Required config key '" + hotValue.value() + "' is not set");
                }

                field.setAccessible(true);
                field.set(bean, value);

                logger.debug("Initialized field {}.{} with value: {}",
                        beanClass.getSimpleName(), field.getName(), value);
            } catch (Exception e) {
                logger.error("Failed to set @HotValue field: " + field.getName(), e);
            }
        }
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
        Field[] fields = clazz.getDeclaredFields();
        Field[] parentFields = null;
        if (clazz.getSuperclass() != null && clazz.getSuperclass() != Object.class) {
            parentFields = getAllFields(clazz.getSuperclass());
        }
        if (parentFields != null && parentFields.length > 0) {
            Field[] result = Arrays.copyOf(fields, fields.length + parentFields.length);
            System.arraycopy(parentFields, 0, result, fields.length, parentFields.length);
            return result;
        }
        return fields;
    }

    @Override
    public void setApplicationContext(ApplicationContext applicationContext) throws BeansException {
        this.applicationContext = applicationContext;
    }

    @Override
    public int getOrder() {
        return PriorityOrdered.HIGHEST_PRECEDENCE + 100;
    }
}
