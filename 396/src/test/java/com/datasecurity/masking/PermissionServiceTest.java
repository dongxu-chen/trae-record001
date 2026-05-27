package com.datasecurity.masking;

import com.datasecurity.masking.access.PermissionService;
import com.datasecurity.masking.access.UserContext;
import com.datasecurity.masking.enums.SensitiveType;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class PermissionServiceTest {

    @Autowired
    private PermissionService permissionService;

    @Test
    void testAdminCanViewSensitiveData() {
        UserContext admin = UserContext.builder()
                .userId("admin001")
                .username("admin")
                .roles(Set.of("ADMIN"))
                .build();

        assertTrue(permissionService.canViewSensitiveData(admin));
        assertTrue(permissionService.canViewSensitiveType(admin, SensitiveType.ID_CARD));
        assertTrue(permissionService.canViewSensitiveType(admin, SensitiveType.PHONE));
        assertTrue(permissionService.canViewSensitiveType(admin, SensitiveType.BANK_CARD));
        assertFalse(permissionService.needMasking(admin));
    }

    @Test
    void testViewerCannotViewSensitiveData() {
        UserContext viewer = UserContext.builder()
                .userId("viewer001")
                .username("viewer")
                .roles(Set.of("VIEWER"))
                .build();

        assertFalse(permissionService.canViewSensitiveData(viewer));
        assertFalse(permissionService.canViewSensitiveType(viewer, SensitiveType.ID_CARD));
        assertFalse(permissionService.canViewSensitiveType(viewer, SensitiveType.PHONE));
        assertTrue(permissionService.needMasking(viewer));
    }

    @Test
    void testOperatorCanViewPartialSensitiveData() {
        UserContext operator = UserContext.builder()
                .userId("operator001")
                .username("operator")
                .roles(Set.of("OPERATOR"))
                .build();

        assertFalse(permissionService.canViewSensitiveData(operator));
        assertTrue(permissionService.canViewSensitiveType(operator, SensitiveType.NAME));
        assertTrue(permissionService.canViewSensitiveType(operator, SensitiveType.PHONE));
        assertFalse(permissionService.canViewSensitiveType(operator, SensitiveType.ID_CARD));
        assertFalse(permissionService.canViewSensitiveType(operator, SensitiveType.BANK_CARD));
        assertTrue(permissionService.needMasking(operator));
    }

    @Test
    void testUserWithPermissionCanViewSensitiveData() {
        UserContext user = UserContext.builder()
                .userId("user001")
                .username("user")
                .roles(Set.of("USER"))
                .permissions(Set.of("VIEW_SENSITIVE_DATA"))
                .build();

        assertTrue(permissionService.canViewSensitiveData(user));
        assertFalse(permissionService.needMasking(user));
    }

    @Test
    void testNullUser() {
        assertFalse(permissionService.canViewSensitiveData(null));
        assertFalse(permissionService.canViewSensitiveType(null, SensitiveType.PHONE));
        assertTrue(permissionService.needMasking(null));
    }

    @Test
    void testNeedMaskingFlag() {
        UserContext user = UserContext.builder()
                .userId("user001")
                .username("user")
                .roles(Set.of("ADMIN"))
                .needMasking(true)
                .build();

        assertTrue(permissionService.needMasking(user));
    }
}
