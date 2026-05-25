package com.mfa.config;

import com.mfa.entity.User;
import com.mfa.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) {
        if (userRepository.count() == 0) {
            User user = new User();
            user.setUsername("testuser");
            user.setEmail("testuser@example.com");
            user.setPhone("13800138000");
            user.setPasswordHash(passwordEncoder.encode("password123"));
            user.setEnabled(true);
            user.setAccountLocked(false);

            userRepository.save(user);
            log.info("Test user created: testuser / password123");
        }
    }
}
