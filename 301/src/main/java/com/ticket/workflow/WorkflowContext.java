package com.ticket.workflow;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Data
@Slf4j
public class WorkflowContext implements Serializable {

    private static final long serialVersionUID = 1L;

    private static final ThreadLocal<WorkflowContext> THREAD_LOCAL = new ThreadLocal<>();

    public static final String KEY = "workflowContext";

    private Long ticketId;
    private String ticketNo;
    private String title;
    private Long creatorId;
    private String creatorName;
    private Long assigneeId;
    private String assigneeName;
    private String department;
    private String ticketType;
    private String priority;
    private String status;
    private Long slaId;
    private LocalDateTime responseDeadline;
    private LocalDateTime resolutionDeadline;
    private LocalDateTime createdAt;
    private String processInstanceId;
    private String parentTicketId;
    private String customFields;

    private final Map<String, Object> variables = new ConcurrentHashMap<>();
    private final Map<String, Object> transientVariables = new ConcurrentHashMap<>();

    public WorkflowContext() {
    }

    public static WorkflowContext create() {
        WorkflowContext context = new WorkflowContext();
        context.setCreatedAt(LocalDateTime.now());
        return context;
    }

    public void setVariable(String key, Object value) {
        variables.put(key, value);
    }

    public Object getVariable(String key) {
        return variables.get(key);
    }

    public <T> T getVariable(String key, Class<T> type) {
        Object value = variables.get(key);
        if (value != null && type.isInstance(value)) {
            return type.cast(value);
        }
        return null;
    }

    public void setTransientVariable(String key, Object value) {
        transientVariables.put(key, value);
    }

    public Object getTransientVariable(String key) {
        return transientVariables.get(key);
    }

    public void removeVariable(String key) {
        variables.remove(key);
    }

    public boolean hasVariable(String key) {
        return variables.containsKey(key);
    }

    public Map<String, Object> getAllVariables() {
        return new HashMap<>(variables);
    }

    public static void setCurrent(WorkflowContext context) {
        THREAD_LOCAL.set(context);
    }

    public static WorkflowContext getCurrent() {
        WorkflowContext context = THREAD_LOCAL.get();
        if (context == null) {
            log.debug("当前线程未设置WorkflowContext，创建新的上下文");
            context = create();
            THREAD_LOCAL.set(context);
        }
        return context;
    }

    public static void clear() {
        THREAD_LOCAL.remove();
    }

    public static WorkflowContext fromMap(Map<String, Object> map) {
        WorkflowContext context = create();
        if (map == null) {
            return context;
        }
        context.setTicketId(getLong(map, "ticketId"));
        context.setTicketNo(getString(map, "ticketNo"));
        context.setTitle(getString(map, "title"));
        context.setCreatorId(getLong(map, "creatorId"));
        context.setCreatorName(getString(map, "creatorName"));
        context.setAssigneeId(getLong(map, "assigneeId"));
        context.setAssigneeName(getString(map, "assigneeName"));
        context.setDepartment(getString(map, "department"));
        context.setTicketType(getString(map, "ticketType"));
        context.setPriority(getString(map, "priority"));
        context.setStatus(getString(map, "status"));
        context.setSlaId(getLong(map, "slaId"));
        context.setResponseDeadline(getLocalDateTime(map, "responseDeadline"));
        context.setResolutionDeadline(getLocalDateTime(map, "resolutionDeadline"));
        context.setCreatedAt(getLocalDateTime(map, "createdAt"));
        context.setProcessInstanceId(getString(map, "processInstanceId"));
        context.setParentTicketId(getString(map, "parentTicketId"));
        context.setCustomFields(getString(map, "customFields"));

        for (Map.Entry<String, Object> entry : map.entrySet()) {
            if (!isReservedKey(entry.getKey())) {
                context.setVariable(entry.getKey(), entry.getValue());
            }
        }

        return context;
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("ticketId", ticketId);
        map.put("ticketNo", ticketNo);
        map.put("title", title);
        map.put("creatorId", creatorId);
        map.put("creatorName", creatorName);
        map.put("assigneeId", assigneeId);
        map.put("assigneeName", assigneeName);
        map.put("department", department);
        map.put("ticketType", ticketType);
        map.put("priority", priority);
        map.put("status", status);
        map.put("slaId", slaId);
        map.put("responseDeadline", responseDeadline);
        map.put("resolutionDeadline", resolutionDeadline);
        map.put("createdAt", createdAt);
        map.put("processInstanceId", processInstanceId);
        map.put("parentTicketId", parentTicketId);
        map.put("customFields", customFields);
        map.putAll(variables);
        return map;
    }

    private static boolean isReservedKey(String key) {
        return key.equals("ticketId") || key.equals("ticketNo") || key.equals("title") ||
               key.equals("creatorId") || key.equals("creatorName") ||
               key.equals("assigneeId") || key.equals("assigneeName") ||
               key.equals("department") || key.equals("ticketType") ||
               key.equals("priority") || key.equals("status") || key.equals("slaId") ||
               key.equals("responseDeadline") || key.equals("resolutionDeadline") ||
               key.equals("createdAt") || key.equals("processInstanceId") ||
               key.equals("parentTicketId") || key.equals("customFields");
    }

    private static Long getLong(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value == null) {
            return null;
        }
        if (value instanceof Long) {
            return (Long) value;
        }
        if (value instanceof Integer) {
            return ((Integer) value).longValue();
        }
        if (value instanceof String) {
            try {
                return Long.parseLong((String) value);
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }

    private static String getString(Map<String, Object> map, String key) {
        Object value = map.get(key);
        return value != null ? value.toString() : null;
    }

    private static LocalDateTime getLocalDateTime(Map<String, Object> map, String key) {
        Object value = map.get(key);
        if (value instanceof LocalDateTime) {
            return (LocalDateTime) value;
        }
        return null;
    }
}
