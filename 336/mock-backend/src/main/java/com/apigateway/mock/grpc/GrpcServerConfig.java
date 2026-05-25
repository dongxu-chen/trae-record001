package com.apigateway.mock.grpc;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.ApplicationListener;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.annotation.PreDestroy;
import java.io.IOException;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class GrpcServerConfig {

    @Value("${grpc.server.port:9090}")
    private int grpcPort;

    private final UserServiceImpl userService;
    private final OrderServiceImpl orderService;
    private Server grpcServer;

    @Bean
    public ApplicationListener<ApplicationReadyEvent> grpcServerStarter() {
        return event -> {
            try {
                startGrpcServer();
            } catch (IOException e) {
                log.error("启动gRPC服务器失败", e);
            }
        };
    }

    private void startGrpcServer() throws IOException {
        grpcServer = ServerBuilder.forPort(grpcPort)
                .addService(userService)
                .addService(orderService)
                .build()
                .start();

        log.info("gRPC服务器已启动，监听端口: {}", grpcPort);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            log.info("JVM关闭钩子，停止gRPC服务器");
            stopGrpcServer();
        }));
    }

    @PreDestroy
    public void stopGrpcServer() {
        if (grpcServer != null && !grpcServer.isShutdown()) {
            grpcServer.shutdown();
            try {
                grpcServer.awaitTermination();
                log.info("gRPC服务器已停止");
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
    }
}
