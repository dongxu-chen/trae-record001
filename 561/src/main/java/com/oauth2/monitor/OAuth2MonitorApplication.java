package com.oauth2.monitor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class OAuth2MonitorApplication {
    public static void main(String[] args) {
        SpringApplication.run(OAuth2MonitorApplication.class, args);
    }
}
