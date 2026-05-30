package com.taskflow.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.taskflow.engine.DagExecutor;
import com.taskflow.engine.TaskQueue;
import com.taskflow.repository.TaskExecutionRepository;
import com.taskflow.repository.TaskRepository;
import com.taskflow.repository.WorkflowExecutionRepository;
import com.taskflow.service.LineageService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.function.Consumer;
import java.util.List;

@Configuration
public class AppConfig {

    @Value("${taskflow.engine.thread-pool-size:8}")
    private int threadPoolSize;

    @Value("${taskflow.engine.high-priority-threshold:8}")
    private int highPriorityThreshold;

    @Bean
    public ThreadPoolTaskExecutor taskFlowExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(threadPoolSize);
        executor.setMaxPoolSize(threadPoolSize * 2);
        executor.setQueueCapacity(500);
        executor.setThreadNamePrefix("taskflow-");
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(60);
        executor.initialize();
        return executor;
    }

    @Bean
    public TaskQueue taskQueue() {
        return new TaskQueue();
    }

    @Bean
    public DagExecutor dagExecutor(TaskRepository taskRepository,
                                   TaskExecutionRepository taskExecutionRepository,
                                   WorkflowExecutionRepository workflowExecutionRepository,
                                   ThreadPoolTaskExecutor taskFlowExecutor,
                                   ObjectMapper objectMapper,
                                   LineageService lineageService) {
        Consumer<List<String>> dataProductCallback = lineageService::triggerDownstreamByDataProducts;
        return new DagExecutor(taskRepository, taskExecutionRepository,
                workflowExecutionRepository, taskFlowExecutor, objectMapper, dataProductCallback);
    }
}
