package com.apiversion.version;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
@MapperScan("com.apiversion.version.mapper")
public class VersionManagerApplication {

    public static void main(String[] args) {
        SpringApplication.run(VersionManagerApplication.class, args);
    }
}
