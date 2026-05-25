package com.taskscheduler.admin;

import com.taskscheduler.core.service.TaskService;
import lombok.extern.slf4j.Slf4j;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

@Slf4j
@SpringBootApplication
@ComponentScan(basePackages = "com.taskscheduler")
@MapperScan(basePackages = "com.taskscheduler.core.mapper")
@EnableScheduling
@EnableAsync
public class TaskSchedulerAdminApplication implements CommandLineRunner {

    @Autowired
    private TaskService taskService;

    public static void main(String[] args) {
        SpringApplication.run(TaskSchedulerAdminApplication.class, args);
        log.info("===============================================");
        log.info("   Task Scheduler Admin started successfully!");
        log.info("   URL: http://localhost:8080");
        log.info("===============================================");
    }

    @Override
    public void run(String... args) throws Exception {
        try {
            taskService.initAllCronTasks();
            log.info("All cron tasks initialized");
        } catch (Exception e) {
            log.error("Initialize cron tasks failed", e);
        }
    }
}
