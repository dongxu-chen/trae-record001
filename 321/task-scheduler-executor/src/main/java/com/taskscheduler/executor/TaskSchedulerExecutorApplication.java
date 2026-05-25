package com.taskscheduler.executor;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.ComponentScan;

@Slf4j
@SpringBootApplication
@ComponentScan(basePackages = "com.taskscheduler")
public class TaskSchedulerExecutorApplication {

    public static ApplicationContext applicationContext;

    public static void main(String[] args) {
        applicationContext = SpringApplication.run(TaskSchedulerExecutorApplication.class, args);
        log.info("===============================================");
        log.info("   Task Scheduler Executor started successfully!");
        log.info("===============================================");
    }
}
