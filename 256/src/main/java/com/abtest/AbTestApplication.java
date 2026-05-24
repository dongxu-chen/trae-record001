package com.abtest;

import com.abtest.service.ClickHouseMetricsService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class AbTestApplication {

    public static void main(String[] args) {
        SpringApplication.run(AbTestApplication.class, args);
    }

    @Bean
    public CommandLineRunner initClickHouse(ClickHouseMetricsService metricsService) {
        return args -> {
            try {
                metricsService.initTables();
            } catch (Exception e) {
                // ClickHouse may not be available during startup, that's okay
            }
        };
    }
}
