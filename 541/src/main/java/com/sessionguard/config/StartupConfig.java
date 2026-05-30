package com.sessionguard.config;

import com.sessionguard.ml.IsolationForestDetector;
import com.sessionguard.service.SessionGuardService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@RequiredArgsConstructor
@Slf4j
public class StartupConfig {

    @Bean
    public CommandLineRunner initMlModel(SessionGuardService sessionGuardService) {
        return args -> {
            log.info("Session Guard initializing - training ML model with synthetic data...");
            try {
                sessionGuardService.trainModel();
                log.info("ML model training completed successfully");
            } catch (Exception e) {
                log.warn("ML model training failed (will work in rule-only mode): {}", e.getMessage());
            }
            log.info("Session Guard started successfully");
        };
    }
}
