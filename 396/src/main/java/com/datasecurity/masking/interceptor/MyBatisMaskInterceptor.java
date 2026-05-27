package com.datasecurity.masking.interceptor;

import com.datasecurity.masking.access.PermissionService;
import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.access.UserContextHolder;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.service.MetadataService;
import com.datasecurity.masking.strategy.MaskStrategyService;
import lombok.extern.slf4j.Slf4j;
import org.apache.ibatis.executor.resultset.ResultSetHandler;
import org.apache.ibatis.plugin.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.sql.Statement;
import java.util.*;

@Slf4j
@Component
@Intercepts({
        @Signature(type = ResultSetHandler.class, method = "handleResultSets", args = {Statement.class})
})
public class MyBatisMaskInterceptor implements Interceptor {

    @Autowired
    private MetadataService metadataService;

    @Autowired
    private MaskStrategyService maskStrategyService;

    @Autowired
    private PermissionService permissionService;

    private String defaultDatabaseId = "default";

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        Object result = invocation.proceed();

        UserContext user = UserContextHolder.get();
        if (!permissionService.needMasking(user)) {
            return result;
        }

        List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields(defaultDatabaseId);
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            return result;
        }

        return maskResultObject(result, sensitiveFields, user);
    }

    @SuppressWarnings("unchecked")
    private Object maskResultObject(Object result, List<SensitiveField> sensitiveFields, UserContext user) {
        if (result instanceof List) {
            List<Object> list = (List<Object>) result;
            List<Object> maskedList = new ArrayList<>();
            for (Object item : list) {
                maskedList.add(maskSingleObject(item, sensitiveFields, user));
            }
            return maskedList;
        } else {
            return maskSingleObject(result, sensitiveFields, user);
        }
    }

    @SuppressWarnings("unchecked")
    private Object maskSingleObject(Object obj, List<SensitiveField> sensitiveFields, UserContext user) {
        if (obj == null) {
            return null;
        }

        if (obj instanceof Map) {
            return maskMap((Map<String, Object>) obj, sensitiveFields, user);
        }

        try {
            for (SensitiveField field : sensitiveFields) {
                String fieldName = field.getColumnName();
                java.lang.reflect.Field objField = findField(obj.getClass(), fieldName);
                if (objField != null) {
                    objField.setAccessible(true);
                    Object value = objField.get(obj);
                    if (value instanceof String) {
                        if (!permissionService.canViewSensitiveType(user, field.getSensitiveType())) {
                            String maskedValue = maskStrategyService.mask((String) value, field.getSensitiveType());
                            objField.set(obj, maskedValue);
                        }
                    }
                }
            }
        } catch (Exception e) {
            log.warn("Failed to mask object of type: {}", obj.getClass().getName(), e);
        }

        return obj;
    }

    private Map<String, Object> maskMap(Map<String, Object> map, List<SensitiveField> sensitiveFields, UserContext user) {
        Map<String, Object> maskedMap = new HashMap<>(map);

        for (SensitiveField field : sensitiveFields) {
            String columnName = field.getColumnName();
            if (maskedMap.containsKey(columnName)) {
                Object value = maskedMap.get(columnName);
                if (value instanceof String) {
                    if (!permissionService.canViewSensitiveType(user, field.getSensitiveType())) {
                        String maskedValue = maskStrategyService.mask((String) value, field.getSensitiveType());
                        maskedMap.put(columnName, maskedValue);
                    }
                }
            }
        }

        return maskedMap;
    }

    private java.lang.reflect.Field findField(Class<?> clazz, String fieldName) {
        Class<?> currentClass = clazz;
        while (currentClass != null && currentClass != Object.class) {
            try {
                return currentClass.getDeclaredField(fieldName);
            } catch (NoSuchFieldException e) {
                currentClass = currentClass.getSuperclass();
            }
        }

        String camelCaseName = toCamelCase(fieldName);
        if (!camelCaseName.equals(fieldName)) {
            currentClass = clazz;
            while (currentClass != null && currentClass != Object.class) {
                try {
                    return currentClass.getDeclaredField(camelCaseName);
                } catch (NoSuchFieldException e) {
                    currentClass = currentClass.getSuperclass();
                }
            }
        }

        return null;
    }

    private String toCamelCase(String snakeCase) {
        StringBuilder result = new StringBuilder();
        boolean nextUpperCase = false;
        for (int i = 0; i < snakeCase.length(); i++) {
            char c = snakeCase.charAt(i);
            if (c == '_') {
                nextUpperCase = true;
            } else {
                if (nextUpperCase) {
                    result.append(Character.toUpperCase(c));
                    nextUpperCase = false;
                } else {
                    result.append(c);
                }
            }
        }
        return result.toString();
    }

    @Override
    public Object plugin(Object target) {
        return Plugin.wrap(target, this);
    }

    @Override
    public void setProperties(Properties properties) {
        this.defaultDatabaseId = properties.getProperty("databaseId", "default");
    }
}
