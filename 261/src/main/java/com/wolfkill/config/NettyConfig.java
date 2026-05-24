package com.wolfkill.config;

import com.wolfkill.netty.NettyServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class NettyConfig {

    private static final Logger logger = LoggerFactory.getLogger(NettyConfig.class);

    @Bean
    public CommandLineRunner nettyServerRunner(NettyServer nettyServer) {
        return args -> {
            logger.info("Starting Netty server...");
            new Thread(() -> {
                try {
                    nettyServer.start();
                } catch (InterruptedException e) {
                    logger.error("Netty server interrupted", e);
                    Thread.currentThread().interrupt();
                }
            }, "netty-server").start();
        };
    }
}
