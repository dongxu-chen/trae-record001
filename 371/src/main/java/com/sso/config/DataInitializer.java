package com.sso.config;

import com.sso.entity.Permission;
import com.sso.entity.Role;
import com.sso.entity.User;
import com.sso.repository.PermissionRepository;
import com.sso.repository.RoleRepository;
import com.sso.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.Set;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final PermissionRepository permissionRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    @Transactional
    public void run(String... args) {
        initializePermissions();
        initializeRoles();
        initializeDefaultUsers();
    }

    private void initializePermissions() {
        if (permissionRepository.count() == 0) {
            Permission userRead = createPermission("user:read", "Read user information", "user", "read");
            Permission userWrite = createPermission("user:write", "Create/Update users", "user", "write");
            Permission userDelete = createPermission("user:delete", "Delete users", "user", "delete");
            Permission roleManage = createPermission("role:manage", "Manage roles and permissions", "role", "manage");
            Permission sessionManage = createPermission("session:manage", "Manage user sessions", "session", "manage");
            Permission clientManage = createPermission("client:manage", "Manage OAuth2/SAML2 clients", "client", "manage");
            Permission syncManage = createPermission("sync:manage", "Manage directory synchronization", "sync", "manage");

            log.info("Initialized default permissions");
        }
    }

    private Permission createPermission(String name, String description, String resource, String action) {
        Permission permission = new Permission();
        permission.setName(name);
        permission.setDescription(description);
        permission.setResource(resource);
        permission.setAction(action);
        return permissionRepository.save(permission);
    }

    private void initializeRoles() {
        if (roleRepository.count() == 0) {
            Role adminRole = new Role();
            adminRole.setName("ADMIN");
            adminRole.setDescription("Administrator role with full access");
            adminRole.setPermissions(new HashSet<>(permissionRepository.findAll()));
            roleRepository.save(adminRole);

            Role userRole = new Role();
            userRole.setName("USER");
            userRole.setDescription("Default user role");
            Set<Permission> userPermissions = new HashSet<>();
            permissionRepository.findByName("user:read").ifPresent(userPermissions::add);
            userRole.setPermissions(userPermissions);
            roleRepository.save(userRole);

            Role managerRole = new Role();
            managerRole.setName("MANAGER");
            managerRole.setDescription("Manager role with user management access");
            Set<Permission> managerPermissions = new HashSet<>();
            permissionRepository.findByName("user:read").ifPresent(managerPermissions::add);
            permissionRepository.findByName("user:write").ifPresent(managerPermissions::add);
            permissionRepository.findByName("session:manage").ifPresent(managerPermissions::add);
            managerRole.setPermissions(managerPermissions);
            roleRepository.save(managerRole);

            log.info("Initialized default roles: ADMIN, USER, MANAGER");
        }
    }

    private void initializeDefaultUsers() {
        if (userRepository.count() == 0) {
            Role adminRole = roleRepository.findByName("ADMIN").orElseThrow();
            Role userRole = roleRepository.findByName("USER").orElseThrow();

            User admin = new User();
            admin.setUsername("admin");
            admin.setPassword(passwordEncoder.encode("admin123"));
            admin.setEmail("admin@example.com");
            admin.setFirstName("System");
            admin.setLastName("Administrator");
            admin.setDisplayName("System Administrator");
            admin.setPhone("+86-000-0000-0001");
            admin.setEnabled(true);
            admin.setAccountNonLocked(true);
            admin.setAccountNonExpired(true);
            admin.setCredentialsNonExpired(true);
            admin.setMfaEnabled(false);
            admin.setRoles(new HashSet<>(Set.of(adminRole, userRole)));
            userRepository.save(admin);
            log.info("Created default admin user: admin / admin123");

            User user = new User();
            user.setUsername("user");
            user.setPassword(passwordEncoder.encode("user123"));
            user.setEmail("user@example.com");
            user.setFirstName("Test");
            user.setLastName("User");
            user.setDisplayName("Test User");
            user.setPhone("+86-000-0000-0002");
            user.setEnabled(true);
            user.setAccountNonLocked(true);
            user.setAccountNonExpired(true);
            user.setCredentialsNonExpired(true);
            user.setMfaEnabled(false);
            user.setRoles(new HashSet<>(Set.of(userRole)));
            userRepository.save(user);
            log.info("Created default test user: user / user123");

            User manager = new User();
            manager.setUsername("manager");
            manager.setPassword(passwordEncoder.encode("manager123"));
            manager.setEmail("manager@example.com");
            manager.setFirstName("Test");
            manager.setLastName("Manager");
            manager.setDisplayName("Test Manager");
            manager.setPhone("+86-000-0000-0003");
            manager.setEnabled(true);
            manager.setAccountNonLocked(true);
            manager.setAccountNonExpired(true);
            manager.setCredentialsNonExpired(true);
            manager.setMfaEnabled(false);
            manager.setRoles(new HashSet<>(Set.of(
                    roleRepository.findByName("MANAGER").orElseThrow(),
                    userRole
            )));
            userRepository.save(manager);
            log.info("Created default manager user: manager / manager123");
        }
    }
}
