package com.configcenter.example;

import com.configcenter.client.ConfigServiceClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import javax.annotation.PostConstruct;

/**
 * 配置中心示例应用
 */
@SpringBootApplication
public class ExampleApplication {

    @Autowired(required = false)
    private ConfigServiceClient configServiceClient;

    public static void main(String[] args) {
        SpringApplication.run(ExampleApplication.class, args);
    }

    @PostConstruct
    public void init() {
        if (configServiceClient != null) {
            System.out.println("========================================");
            System.out.println("配置中心客户端已启动");
            System.out.println("客户端ID: " + configServiceClient.getClientId());
            System.out.println("连接状态: " + configServiceClient.isConnected());
            System.out.println("========================================");
        }
    }
}
