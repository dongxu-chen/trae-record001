package com.sso.service;

import com.sso.entity.User;
import com.sso.entity.Role;
import com.sso.repository.UserRepository;
import com.sso.repository.RoleRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserRequest;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.oidc.OidcIdToken;
import org.springframework.security.oauth2.core.oidc.OidcUserInfo;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUserAuthority;
import org.springframework.stereotype.Service;

import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class SocialLoginUserService extends OidcUserService {

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;

    @Override
    public OidcUser loadUser(OidcUserRequest userRequest) throws OAuth2AuthenticationException {
        OidcUser oidcUser = super.loadUser(userRequest);

        String registrationId = userRequest.getClientRegistration().getRegistrationId();
        String email = oidcUser.getEmail();
        String name = oidcUser.getFullName();
        String providerUserId = oidcUser.getSubject();

        log.info("Social login attempt: provider={}, email={}, name={}", registrationId, email, name);

        User user = userRepository.findByEmail(email)
                .orElseGet(() -> createSocialUser(registrationId, email, name, providerUserId));

        if (!user.isEnabled()) {
            throw new OAuth2AuthenticationException("User account is disabled");
        }

        log.info("Social login successful for user: {}, provider: {}", user.getUsername(), registrationId);
        return buildOidcUser(oidcUser, user);
    }

    private User createSocialUser(String provider, String email, String name, String providerUserId) {
        String username = generateUsername(provider, providerUserId);

        User user = new User();
        user.setUsername(username);
        user.setEmail(email);
        user.setDisplayName(name != null ? name : email);
        user.setPassword(UUID.randomUUID().toString());
        user.setEnabled(true);
        user.setLdapUser(false);
        user.setMfaEnabled(false);

        Role defaultRole = roleRepository.findByName("USER")
                .orElseThrow(() -> new OAuth2AuthenticationException("Default role not found"));
        user.setRoles(new HashSet<>(Collections.singletonList(defaultRole)));

        User savedUser = userRepository.save(user);
        log.info("Created social user: username={}, provider={}, email={}", username, provider, email);

        return savedUser;
    }

    private String generateUsername(String provider, String providerUserId) {
        String base = provider + "_" + (providerUserId.length() > 8 ? providerUserId.substring(0, 8) : providerUserId);
        String username = base;
        int counter = 1;

        while (userRepository.existsByUsername(username)) {
            username = base + "_" + counter++;
        }

        return username;
    }

    private OidcUser buildOidcUser(OidcUser oidcUser, User user) {
        OidcIdToken idToken = oidcUser.getIdToken();
        OidcUserInfo userInfo = oidcUser.getUserInfo();

        Set<OidcUserAuthority> authorities = new HashSet<>();
        authorities.add(new OidcUserAuthority(idToken, userInfo));

        for (Role role : user.getRoles()) {
            authorities.add(new OidcUserAuthority("ROLE_" + role.getName(), idToken, userInfo));
        }

        Map<String, Object> claims = new HashMap<>(oidcUser.getClaims());
        claims.put("local_username", user.getUsername());
        claims.put("user_roles", user.getRoles().stream().map(Role::getName).toList());

        return new DefaultOidcUser(authorities, idToken, userInfo);
    }
}
