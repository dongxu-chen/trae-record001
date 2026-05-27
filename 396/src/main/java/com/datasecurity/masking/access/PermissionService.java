package com.datasecurity.masking.access;

import com.datasecurity.masking.enums.SensitiveType;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

@Service
public class PermissionService {

    private static final String PERMISSION_VIEW_SENSITIVE = "VIEW_SENSITIVE_DATA";

    private static final Set<String> ADMIN_ROLES = Set.of("ADMIN", "SUPER_ADMIN", "DBA");

    private final Map<String, Set<SensitiveType>> roleSensitiveTypeMap = new HashMap<>();

    public PermissionService() {
        roleSensitiveTypeMap.put("ADMIN", Set.of(SensitiveType.values()));
        roleSensitiveTypeMap.put("DBA", Set.of(SensitiveType.values()));
        roleSensitiveTypeMap.put("OPERATOR", Set.of(SensitiveType.NAME, SensitiveType.PHONE));
        roleSensitiveTypeMap.put("VIEWER", Set.of());
    }

    public boolean canViewSensitiveData(UserContext user) {
        if (user == null) {
            return false;
        }

        if (user.getRoles() != null) {
            for (String role : user.getRoles()) {
                if (ADMIN_ROLES.contains(role)) {
                    return true;
                }
            }
        }

        if (user.getPermissions() != null && user.getPermissions().contains(PERMISSION_VIEW_SENSITIVE)) {
            return true;
        }

        return false;
    }

    public boolean canViewSensitiveType(UserContext user, SensitiveType sensitiveType) {
        if (user == null || sensitiveType == null) {
            return false;
        }

        if (canViewSensitiveData(user)) {
            return true;
        }

        if (user.getRoles() != null) {
            for (String role : user.getRoles()) {
                Set<SensitiveType> allowedTypes = roleSensitiveTypeMap.get(role);
                if (allowedTypes != null && allowedTypes.contains(sensitiveType)) {
                    return true;
                }
            }
        }

        return false;
    }

    public boolean needMasking(UserContext user) {
        if (user == null) {
            return true;
        }
        if (user.isNeedMasking()) {
            return true;
        }
        return !canViewSensitiveData(user);
    }
}
