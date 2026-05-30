package com.hotconfig.core.proxy;

import com.hotconfig.annotation.HotValue;
import com.hotconfig.core.ConfigManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;

public class HotConfigInvocationHandler implements InvocationHandler {

    private static final Logger logger = LoggerFactory.getLogger(HotConfigInvocationHandler.class);

    private final Object target;
    private final String prefix;
    private final ConfigManager configManager;

    public HotConfigInvocationHandler(Object target, String prefix, ConfigManager configManager) {
        this.target = target;
        this.prefix = prefix;
        this.configManager = configManager;
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        String methodName = method.getName();

        if ("toString".equals(methodName) && args == null) {
            return "HotConfigProxy[" + target.getClass().getName() + "]";
        }
        if ("hashCode".equals(methodName) && args == null) {
            return target.hashCode();
        }
        if ("equals".equals(methodName) && args != null && args.length == 1) {
            return target.equals(args[0]);
        }

        if (methodName.startsWith("get") && methodName.length() > 3
                && (args == null || args.length == 0)) {
            String fieldName = decapitalize(methodName.substring(3));
            Field field = findField(target.getClass(), fieldName);

            if (field != null && field.isAnnotationPresent(HotValue.class)) {
                HotValue hotValue = field.getAnnotation(HotValue.class);
                String configKey = hotValue.value();
                String fullKey = prefix.isEmpty() ? configKey : prefix + "." + configKey;

                try {
                    Object value = configManager.getValue(fullKey, field.getType(), hotValue.defaultValue());
                    if (value != null) {
                        logger.trace("Returning hot value for key '{}': {}", fullKey, value);
                        return value;
                    }
                } catch (Exception e) {
                    logger.warn("Failed to get hot value for key '{}', falling back to field value: {}",
                            fullKey, e.getMessage());
                }
            }
        }

        if (methodName.startsWith("set") && methodName.length() > 3 && args != null && args.length == 1) {
            String fieldName = decapitalize(methodName.substring(3));
            Field field = findField(target.getClass(), fieldName);

            if (field != null && field.isAnnotationPresent(HotValue.class)) {
                HotValue hotValue = field.getAnnotation(HotValue.class);
                String configKey = hotValue.value();
                String fullKey = prefix.isEmpty() ? configKey : prefix + "." + configKey;

                logger.debug("Setting local value for key '{}': {}", fullKey, args[0]);
                configManager.setLocalValue(fullKey, args[0]);
            }
        }

        return method.invoke(target, args);
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

    public Object getTarget() {
        return target;
    }
}
