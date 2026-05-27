package com.datasecurity.masking.aspect;

import com.datasecurity.masking.annotation.DataMasking;
import com.datasecurity.masking.proxy.DataMaskingProxy;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;

@Slf4j
@Aspect
@Component
@Order(1)
public class DataMaskingAspect {

    @Autowired
    private DataMaskingProxy dataMaskingProxy;

    @Around("@annotation(com.datasecurity.masking.annotation.DataMasking) || @within(com.datasecurity.masking.annotation.DataMasking)")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Method method = signature.getMethod();

        DataMasking dataMasking = method.getAnnotation(DataMasking.class);
        if (dataMasking == null) {
            Class<?> targetClass = joinPoint.getTarget().getClass();
            dataMasking = targetClass.getAnnotation(DataMasking.class);
        }

        if (dataMasking == null || !dataMasking.enabled()) {
            return joinPoint.proceed();
        }

        String databaseId = dataMasking.databaseId();
        Object result = joinPoint.proceed();

        if (result == null) {
            return null;
        }

        try {
            Object maskedResult = maskResult(result, databaseId);
            log.debug("Data masking applied for method: {}, databaseId: {}", method.getName(), databaseId);
            return maskedResult;
        } catch (Exception e) {
            log.error("Failed to apply data masking for method: {}", method.getName(), e);
            return result;
        }
    }

    @SuppressWarnings("unchecked")
    private Object maskResult(Object result, String databaseId) {
        if (result instanceof List) {
            List<?> list = (List<?>) result;
            if (!list.isEmpty() && list.get(0) instanceof Map) {
                return dataMaskingProxy.maskResult((List<Map<String, Object>>) list, databaseId);
            }
        } else if (result instanceof Map) {
            return dataMaskingProxy.maskRow((Map<String, Object>) result, databaseId);
        }
        return result;
    }
}
