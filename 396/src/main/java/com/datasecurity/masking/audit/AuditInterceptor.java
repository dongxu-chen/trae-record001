package com.datasecurity.masking.audit;

import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.access.UserContextHolder;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.service.MetadataService;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.servlet.http.HttpServletRequest;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Aspect
@Component
@Order(Ordered.LOWEST_PRECEDENCE)
public class AuditInterceptor {

    @Autowired
    private AuditLogStore auditLogStore;

    @Autowired
    private MetadataService metadataService;

    @Around("@annotation(com.datasecurity.masking.audit.Auditable) || @within(com.datasecurity.masking.audit.Auditable)")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        long startTime = System.currentTimeMillis();
        Object result = null;
        Exception exception = null;

        try {
            result = joinPoint.proceed();
            return result;
        } catch (Exception e) {
            exception = e;
            throw e;
        } finally {
            try {
                recordAuditLog(joinPoint, result, exception, System.currentTimeMillis() - startTime);
            } catch (Exception e) {
                log.warn("Failed to record audit log", e);
            }
        }
    }

    private void recordAuditLog(ProceedingJoinPoint joinPoint, Object result, Exception exception, long executionTime) {
        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        Auditable auditable = signature.getMethod().getAnnotation(Auditable.class);
        if (auditable == null) {
            auditable = joinPoint.getTarget().getClass().getAnnotation(Auditable.class);
        }

        if (auditable == null) {
            return;
        }

        UserContext userContext = UserContextHolder.get();

        AuditLog auditLog = AuditLog.builder()
                .userId(userContext != null ? userContext.getUserId() : "anonymous")
                .username(userContext != null ? userContext.getUsername() : "anonymous")
                .userRole(userContext != null && userContext.getRoles() != null
                        ? String.join(",", userContext.getRoles()) : "unknown")
                .operation(auditable.operation())
                .executionTime(executionTime)
                .build();

        HttpServletRequest request = getCurrentRequest();
        if (request != null) {
            auditLog.setClientIp(getClientIp(request));
            auditLog.setUserAgent(request.getHeader("User-Agent"));
            auditLog.setRequestId(request.getHeader("X-Request-ID"));
        }

        if (result instanceof List) {
            auditLog.setRowCount(((List<?>) result).size());
        }

        Object[] args = joinPoint.getArgs();
        for (Object arg : args) {
            if (arg instanceof String && ((String) arg).toUpperCase().startsWith("SELECT")) {
                auditLog.setSql((String) arg);
            }
        }

        try {
            List<SensitiveField> sensitiveFields = metadataService.getSensitiveFields(auditable.databaseId());
            if (sensitiveFields != null) {
                List<String> columns = new ArrayList<>();
                List<String> types = new ArrayList<>();
                for (SensitiveField field : sensitiveFields) {
                    columns.add(field.getColumnName());
                    types.add(field.getSensitiveType().name());
                }
                auditLog.setSensitiveColumns(columns);
                auditLog.setSensitiveTypes(types);
            }
        } catch (Exception e) {
            log.warn("Failed to get sensitive fields for audit", e);
        }

        auditLogStore.save(auditLog);
    }

    private HttpServletRequest getCurrentRequest() {
        try {
            ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            return attributes != null ? attributes.getRequest() : null;
        } catch (Exception e) {
            return null;
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }
}
