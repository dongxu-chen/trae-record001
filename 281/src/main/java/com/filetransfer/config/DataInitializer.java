package com.filetransfer.config;

import com.filetransfer.entity.User;
import com.filetransfer.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {
    private final UserRepository userRepository;

    @Override
    public void run(String... args) {
        if (!userRepository.existsByUsername("admin")) {
            User admin = new User();
            admin.setUsername("admin");
            admin.setPassword("admin123");
            admin.setEmail("admin@example.com");
            admin.setStorageQuota(100 * 1024 * 1024 * 1024L);
            admin.setUsedStorage(0L);
            admin.setIsActive(true);
            userRepository.save(admin);
        }

        if (!userRepository.existsByUsername("test")) {
            User test = new User();
            test.setUsername("test");
            test.setPassword("test123");
            test.setEmail("test@example.com");
            test.setStorageQuota(10 * 1024 * 1024 * 1024L);
            test.setUsedStorage(0L);
            test.setIsActive(true);
            userRepository.save(test);
        }
    }
}
