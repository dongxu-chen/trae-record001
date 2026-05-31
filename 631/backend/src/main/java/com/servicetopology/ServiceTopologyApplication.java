package com.servicetopology;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.neo4j.repository.config.EnableNeo4jRepositories;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableNeo4jRepositories
@EnableScheduling
public class ServiceTopologyApplication {

    public static void main(String[] args) {
        SpringApplication.run(ServiceTopologyApplication.class, args);
    }
}
