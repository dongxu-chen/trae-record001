package com.configcenter.admin;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.netflix.eureka.EnableEurekaClient;

@SpringBootApplication
@EnableEurekaClient
public class ConfigAdminApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigAdminApplication.class, args);
    }
}
