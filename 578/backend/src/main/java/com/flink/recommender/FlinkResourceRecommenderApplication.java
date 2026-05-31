package com.flink.recommender;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class FlinkResourceRecommenderApplication {

    public static void main(String[] args) {
        SpringApplication.run(FlinkResourceRecommenderApplication.class, args);
    }
}
