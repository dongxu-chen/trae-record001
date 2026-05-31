package com.log.mask.dynamic;

import java.util.*;

public class AccessContext {
    private final String userId;
    private final String role;
    private final Set<String> permissions = new HashSet<>();
    private final Map<String, Object> attributes = new HashMap<>();

    public AccessContext(String userId, String role) {
        this.userId = userId;
        this.role = role;
    }

    public static AccessContext of(String userId, String role) {
        return new AccessContext(userId, role);
    }

    public static AccessContext admin(String userId) {
        AccessContext ctx = new AccessContext(userId, "ADMIN");
        ctx.permissions.add("sensitive:full");
        ctx.permissions.add("sensitive:partial");
        ctx.permissions.add("sensitive:view_type");
        return ctx;
    }

    public static AccessContext operator(String userId) {
        AccessContext ctx = new AccessContext(userId, "OPERATOR");
        ctx.permissions.add("sensitive:partial");
        ctx.permissions.add("sensitive:view_type");
        return ctx;
    }

    public static AccessContext viewer(String userId) {
        AccessContext ctx = new AccessContext(userId, "VIEWER");
        ctx.permissions.add("sensitive:view_type");
        return ctx;
    }

    public static AccessContext anonymous() {
        return new AccessContext("anonymous", "ANONYMOUS");
    }

    public AccessContext addPermission(String permission) {
        permissions.add(permission);
        return this;
    }

    public AccessContext addPermissions(Collection<String> perms) {
        permissions.addAll(perms);
        return this;
    }

    public boolean hasPermission(String permission) {
        return permissions.contains(permission);
    }

    public MaskPolicy resolvePolicy(String dataType) {
        if (hasPermission("sensitive:full")) {
            return MaskPolicy.FULL;
        }
        if (hasPermission("sensitive:partial:" + dataType) || hasPermission("sensitive:partial")) {
            return MaskPolicy.PARTIAL;
        }
        return MaskPolicy.COMPLETE;
    }

    public String getUserId() { return userId; }
    public String getRole() { return role; }
    public Set<String> getPermissions() { return Collections.unmodifiableSet(permissions); }
    public Map<String, Object> getAttributes() { return attributes; }
    public void setAttribute(String key, Object value) { attributes.put(key, value); }
    public Object getAttribute(String key) { return attributes.get(key); }

    @Override
    public String toString() {
        return "AccessContext{user='" + userId + "', role='" + role + "', perms=" + permissions + "}";
    }
}
