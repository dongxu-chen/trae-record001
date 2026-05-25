package com.apigateway.grpc.bridge;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * gRPC客户端配置属性类
 * 用于配置gRPC客户端的连接参数、连接池、截止时间等
 */
@Data
@ConfigurationProperties(prefix = "grpc.client")
public class GrpcClientProperties {

    /**
     * 默认主机地址
     */
    private String defaultHost = "localhost";

    /**
     * 默认端口号
     */
    private int defaultPort = 9090;

    /**
     * 默认截止时间（毫秒）
     */
    private Duration defaultDeadline = Duration.ofSeconds(30);

    /**
     * 连接池配置
     */
    private PoolProperties pool = new PoolProperties();

    /**
     * Netty通道配置
     */
    private NettyProperties netty = new NettyProperties();

    /**
     * 多服务配置，key为服务名
     */
    private Map<String, ServiceProperties> services = new HashMap<>();

    /**
     * 连接池配置属性
     */
    @Data
    public static class PoolProperties {

        /**
         * 最大连接数
         */
        private int maxConnections = 10;

        /**
         * 最小空闲连接数
         */
        private int minIdleConnections = 2;

        /**
         * 连接最大空闲时间（毫秒）
         */
        private Duration maxIdleTime = Duration.ofMinutes(5);

        /**
         * 连接最大生命周期（毫秒）
         */
        private Duration maxLifeTime = Duration.ofMinutes(30);

        /**
         * 获取连接超时时间（毫秒）
         */
        private Duration acquisitionTimeout = Duration.ofSeconds(10);
    }

    /**
     * Netty通道配置属性
     */
    @Data
    public static class NettyProperties {

        /**
         * 连接超时时间（毫秒）
         */
        private Duration connectTimeout = Duration.ofSeconds(5);

        /**
         * 保持连接
         */
        private boolean keepAlive = true;

        /**
         * 保持连接间隔（毫秒）
         */
        private Duration keepAliveTime = Duration.ofMinutes(2);

        /**
         * 保持连接超时（毫秒）
         */
        private Duration keepAliveTimeout = Duration.ofSeconds(20);

        /**
         * 无延迟（禁用Nagle算法）
         */
        private boolean noDelay = true;

        /**
         * 流控制窗口大小（字节）
         */
        private int flowControlWindow = 1048576;

        /**
         * 最大消息大小（字节）
         */
        private int maxMessageSize = 4194304;
    }

    /**
     * 单个服务配置属性
     */
    @Data
    public static class ServiceProperties {

        /**
         * 服务主机地址
         */
        private String host;

        /**
         * 服务端口号
         */
        private Integer port;

        /**
         * 截止时间（毫秒）
         */
        private Duration deadline;

        /**
         * 是否启用TLS
         */
        private boolean tlsEnabled = false;

        /**
         * TLS证书路径
         */
        private String tlsCertPath;
    }

    /**
     * 获取指定服务的配置，如果不存在则返回默认配置
     *
     * @param serviceName 服务名
     * @return 服务配置
     */
    public ServiceProperties getServiceProperties(String serviceName) {
        return services.getOrDefault(serviceName, new ServiceProperties());
    }

    /**
     * 获取服务主机，如果未配置则返回默认主机
     *
     * @param serviceName 服务名
     * @return 主机地址
     */
    public String getHost(String serviceName) {
        ServiceProperties serviceProps = getServiceProperties(serviceName);
        return serviceProps.getHost() != null ? serviceProps.getHost() : defaultHost;
    }

    /**
     * 获取服务端口，如果未配置则返回默认端口
     *
     * @param serviceName 服务名
     * @return 端口号
     */
    public int getPort(String serviceName) {
        ServiceProperties serviceProps = getServiceProperties(serviceName);
        return serviceProps.getPort() != null ? serviceProps.getPort() : defaultPort;
    }

    /**
     * 获取截止时间，如果未配置则返回默认截止时间
     *
     * @param serviceName 服务名
     * @return 截止时间
     */
    public Duration getDeadline(String serviceName) {
        ServiceProperties serviceProps = getServiceProperties(serviceName);
        return serviceProps.getDeadline() != null ? serviceProps.getDeadline() : defaultDeadline;
    }
}
