package com.sso.service;

import com.sso.entity.Permission;
import com.sso.entity.Role;
import com.sso.entity.User;
import com.sso.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService {

    private final UserRepository userRepository;

    @Override
    @Transactional(readOnly = true)
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new UsernameNotFoundException("User not found with username: " + username));

        if (!user.isEnabled()) {
            throw new UsernameNotFoundException("User account is disabled");
        }

        if (user.isAccountLocked()) {
            throw new UsernameNotFoundException("User account is locked");
        }

        List<SimpleGrantedAuthority> authorities = new ArrayList<>();

        for (Role role : user.getRoles()) {
            authorities.add(new SimpleGrantedAuthority("ROLE_" + role.getName()));
            for (Permission permission : role.getPermissions()) {
                authorities.add(new SimpleGrantedAuthority(permission.getName()));
            }
        }

        return org.springframework.security.core.userdetails.User
                .withUsername(user.getUsername())
                .password(user.getPassword())
                .disabled(!user.isEnabled())
                .accountExpired(!user.isAccountNonExpired())
                .credentialsExpired(!user.isCredentialsNonExpired())
                .accountLocked(user.isAccountLocked())
                .authorities(authorities)
                .build();
    }

    @Transactional
    public void handleLoginSuccess(String username, String ipAddress) {
        User user = userRepository.findByUsername(username).orElse(null);
        if (user != null) {
            userRepository.resetFailedAttempts(username);
            userRepository.updateLastLogin(username, java.time.LocalDateTime.now(), ipAddress);
            log.info("User {} logged in successfully from IP: {}", username, ipAddress);
        }
    }

    @Transactional
    public void handleLoginFailure(String username, String ipAddress) {
        User user = userRepository.findByUsername(username).orElse(null);
        if (user != null) {
            userRepository.incrementFailedAttempts(username);
            int maxAttempts = 5;
            if (user.getFailedAttempts() + 1 >= maxAttempts) {
                userRepository.lockAccount(username, java.time.LocalDateTime.now().plusMinutes(30));
                log.warn("User {} account locked due to too many failed attempts from IP: {}", username, ipAddress);
            }
            log.warn("Login failed for user {} from IP: {}. Attempts: {}", username, ipAddress, user.getFailedAttempts() + 1);
        }
    }
}
