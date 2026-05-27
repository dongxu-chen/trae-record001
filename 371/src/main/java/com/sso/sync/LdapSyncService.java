package com.sso.sync;

import com.sso.config.properties.SsoProperties;
import com.sso.entity.Role;
import com.sso.entity.User;
import com.sso.repository.RoleRepository;
import com.sso.repository.UserRepository;
import com.sso.service.UserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.ldap.core.AttributesMapper;
import org.springframework.ldap.core.LdapTemplate;
import org.springframework.ldap.query.LdapQueryBuilder;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.naming.NamingException;
import javax.naming.directory.Attributes;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Slf4j
@Service
@ConditionalOnProperty(name = "sso.ldap.enabled", havingValue = "true")
@RequiredArgsConstructor
public class LdapSyncService {

    private final LdapTemplate ldapTemplate;
    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final UserService userService;
    private final SsoProperties ssoProperties;

    private static final Map<String, String> DEFAULT_ATTRIBUTE_MAPPING = Map.of(
            "username", "uid",
            "email", "mail",
            "firstName", "givenName",
            "lastName", "sn",
            "phone", "telephoneNumber",
            "displayName", "displayName"
    );

    @Scheduled(cron = "${sso.sync.ldap-sync-cron:0 0 2 * * ?}")
    @Transactional
    public void syncLdapUsers() {
        if (!ssoProperties.getLdap().isEnabled()) {
            log.debug("LDAP sync disabled, skipping");
            return;
        }

        log.info("Starting LDAP user synchronization");

        try {
            SsoProperties.LdapProperties ldapProps = ssoProperties.getLdap();
            String userBase = ldapProps.getUserDnPattern() != null
                    ? ldapProps.getUserDnPattern().replace("uid={0},", "")
                    : "ou=users";

            List<LdapUser> ldapUsers = ldapTemplate.search(
                    LdapQueryBuilder.query().base(userBase).where("objectClass").is("person"),
                    new LdapUserAttributesMapper()
            );

            log.info("Found {} users in LDAP", ldapUsers.size());

            for (LdapUser ldapUser : ldapUsers) {
                syncUser(ldapUser);
            }

            log.info("LDAP user synchronization completed successfully");
        } catch (Exception e) {
            log.error("LDAP user synchronization failed", e);
        }
    }

    private void syncUser(LdapUser ldapUser) {
        try {
            User existingUser = userRepository.findByUsername(ldapUser.username).orElse(null);

            if (existingUser == null) {
                existingUser = userRepository.findByEmail(ldapUser.email).orElse(null);
            }

            User user;
            if (existingUser == null) {
                user = new User();
                user.setUsername(ldapUser.username);
                user.setEmail(ldapUser.email != null ? ldapUser.email : ldapUser.username + "@ldap.local");
                user.setPassword("{LDAP}");
                user.setLdapUser(true);
                user.setLdapDn(ldapUser.dn);
                user.setEnabled(true);
                user.setRoles(getDefaultRoles());

                updateUserFromLdap(user, ldapUser);
                userRepository.save(user);
                log.info("Created new user from LDAP: {}", ldapUser.username);
            } else {
                boolean updated = updateUserFromLdap(existingUser, ldapUser);
                if (updated) {
                    existingUser.setLdapUser(true);
                    existingUser.setLdapDn(ldapUser.dn);
                    userRepository.save(existingUser);
                    log.info("Updated user from LDAP: {}", ldapUser.username);
                }
            }
        } catch (Exception e) {
            log.error("Failed to sync LDAP user: {}", ldapUser.username, e);
        }
    }

    private boolean updateUserFromLdap(User user, LdapUser ldapUser) {
        boolean updated = false;

        if (ldapUser.email != null && !ldapUser.email.equals(user.getEmail())) {
            user.setEmail(ldapUser.email);
            updated = true;
        }
        if (ldapUser.firstName != null && !ldapUser.firstName.equals(user.getFirstName())) {
            user.setFirstName(ldapUser.firstName);
            updated = true;
        }
        if (ldapUser.lastName != null && !ldapUser.lastName.equals(user.getLastName())) {
            user.setLastName(ldapUser.lastName);
            updated = true;
        }
        if (ldapUser.phone != null && !ldapUser.phone.equals(user.getPhone())) {
            user.setPhone(ldapUser.phone);
            updated = true;
        }
        if (ldapUser.displayName != null && !ldapUser.displayName.equals(user.getDisplayName())) {
            user.setDisplayName(ldapUser.displayName);
            updated = true;
        }

        return updated;
    }

    private Set<Role> getDefaultRoles() {
        Set<Role> roles = new HashSet<>();
        Role userRole = roleRepository.findByName("USER").orElseGet(() -> {
            Role role = new Role();
            role.setName("USER");
            role.setDescription("Default user role");
            return roleRepository.save(role);
        });
        roles.add(userRole);
        return roles;
    }

    private static class LdapUser {
        String dn;
        String username;
        String email;
        String firstName;
        String lastName;
        String phone;
        String displayName;
    }

    private static class LdapUserAttributesMapper implements AttributesMapper<LdapUser> {
        @Override
        public LdapUser mapFromAttributes(Attributes attributes) throws NamingException {
            LdapUser user = new LdapUser();
            user.dn = getAttribute(attributes, "dn");
            user.username = getAttribute(attributes, DEFAULT_ATTRIBUTE_MAPPING.get("username"));
            user.email = getAttribute(attributes, DEFAULT_ATTRIBUTE_MAPPING.get("email"));
            user.firstName = getAttribute(attributes, DEFAULT_ATTRIBUTE_MAPPING.get("firstName"));
            user.lastName = getAttribute(attributes, DEFAULT_ATTRIBUTE_MAPPING.get("lastName"));
            user.phone = getAttribute(attributes, DEFAULT_ATTRIBUTE_MAPPING.get("phone"));
            user.displayName = getAttribute(attributes, DEFAULT_ATTRIBUTE_MAPPING.get("displayName"));
            return user;
        }

        private String getAttribute(Attributes attributes, String name) throws NamingException {
            if (attributes.get(name) != null) {
                Object value = attributes.get(name).get();
                return value != null ? value.toString() : null;
            }
            return null;
        }
    }

    public void manualSync() {
        syncLdapUsers();
    }

    public void syncSingleUser(String username) {
        if (!ssoProperties.getLdap().isEnabled()) {
            throw new RuntimeException("LDAP sync is disabled");
        }

        try {
            SsoProperties.LdapProperties ldapProps = ssoProperties.getLdap();
            String userDn = ldapProps.getUserDnPattern().replace("{0}", username);

            LdapUser ldapUser = ldapTemplate.lookup(
                    userDn,
                    new LdapUserAttributesMapper()
            );

            syncUser(ldapUser);
            log.info("Synchronized single LDAP user: {}", username);
        } catch (Exception e) {
            log.error("Failed to sync LDAP user: {}", username, e);
            throw new RuntimeException("Failed to sync LDAP user: " + username, e);
        }
    }
}
