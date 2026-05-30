package com.apiversion.business.v2;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
public class BusinessV2Application {
    public static void main(String[] args) {
        SpringApplication.run(BusinessV2Application.class, args);
    }
}
