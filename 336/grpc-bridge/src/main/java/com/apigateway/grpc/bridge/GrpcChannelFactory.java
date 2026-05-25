package com.apigateway.grpc.bridge;

import com.apigateway.grpc.bridge.exception.GrpcBridgeException;
import io.grpc.ManagedChannel;
import io.grpc.netty.shaded.io.grpc.netty.GrpcSslContexts;
import io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder;
import io.grpc.netty.shaded.io.netty.channel.ChannelOption;
import io.grpc.netty.shaded.io.netty.channel.nio.NioEventLoopGroup;
import io.grpc.netty.shaded.io.netty.channel.socket.nio.NioSocketChannel;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.net.ssl.SSLException;
import java.io.File;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * gRPC通道工厂类
 * 负责管理gRPC连接池，使用Netty作为底层通信框架
 * 支持多服务通道缓存和连接生命周期管理
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class GrpcChannelFactory {

    /**
     * gRPC客户端配置属性
     */
    private final GrpcClientProperties properties;

    /**
     * 通道缓存，key为服务名
     */
    private final Map<String, ManagedChannel> channelCache = new ConcurrentHashMap<>();

    /**
     * 通道引用计数，用于连接池管理
     */
    private final Map<String, AtomicInteger> channelRefCount = new ConcurrentHashMap<>();

    /**
     * Netty事件循环组，共享给所有通道使用
     */
    private final NioEventLoopGroup eventLoopGroup = new NioEventLoopGroup();

    /**
     * 获取或创建指定服务的gRPC通道
     *
     * @param serviceName 服务名
     * @return gRPC ManagedChannel
     */
    public ManagedChannel getChannel(String serviceName) {
        return channelCache.computeIfAbsent(serviceName, this::createChannel);
    }

    /**
     * 借用通道（增加引用计数）
     *
     * @param serviceName 服务名
     * @return gRPC ManagedChannel
     */
    public ManagedChannel borrowChannel(String serviceName) {
        ManagedChannel channel = getChannel(serviceName);
        channelRefCount.computeIfAbsent(serviceName, k -> new AtomicInteger(0)).incrementAndGet();
        log.debug("Borrowed channel for service: {}, ref count: {}", serviceName,
                channelRefCount.get(serviceName).get());
        return channel;
    }

    /**
     * 归还通道（减少引用计数）
     *
     * @param serviceName 服务名
     */
    public void returnChannel(String serviceName) {
        AtomicInteger refCount = channelRefCount.get(serviceName);
        if (refCount != null && refCount.get() > 0) {
            int count = refCount.decrementAndGet();
            log.debug("Returned channel for service: {}, ref count: {}", serviceName, count);
        }
    }

    /**
     * 创建新的gRPC通道
     *
     * @param serviceName 服务名
     * @return 新创建的ManagedChannel
     */
    private ManagedChannel createChannel(String serviceName) {
        String host = properties.getHost(serviceName);
        int port = properties.getPort(serviceName);
        GrpcClientProperties.ServiceProperties serviceProps = properties.getServiceProperties(serviceName);
        GrpcClientProperties.NettyProperties nettyProps = properties.getNetty();

        log.info("Creating gRPC channel for service: {} at {}:{}", serviceName, host, port);

        try {
            NettyChannelBuilder builder = NettyChannelBuilder.forAddress(host, port)
                    .channelType(NioSocketChannel.class)
                    .eventLoopGroup(eventLoopGroup)
                    .withOption(ChannelOption.CONNECT_TIMEOUT_MILLIS,
                            (int) nettyProps.getConnectTimeout().toMillis())
                    .withOption(ChannelOption.SO_KEEPALIVE, nettyProps.isKeepAlive())
                    .withOption(ChannelOption.TCP_NODELAY, nettyProps.isNoDelay())
                    .keepAliveTime(nettyProps.getKeepAliveTime().toMillis(), TimeUnit.MILLISECONDS)
                    .keepAliveTimeout(nettyProps.getKeepAliveTimeout().toMillis(), TimeUnit.MILLISECONDS)
                    .flowControlWindow(nettyProps.getFlowControlWindow())
                    .maxInboundMessageSize(nettyProps.getMaxMessageSize())
                    .idleTimeout(properties.getPool().getMaxIdleTime().toMillis(), TimeUnit.MILLISECONDS);

            if (serviceProps.isTlsEnabled()) {
                configureTls(builder, serviceProps);
            } else {
                builder.usePlaintext();
            }

            ManagedChannel channel = builder.build();
            log.info("Successfully created gRPC channel for service: {}", serviceName);
            return channel;
        } catch (Exception e) {
            throw new GrpcBridgeException("CHANNEL_CREATE_ERROR",
                    String.format("Failed to create gRPC channel for service %s: %s", serviceName, e.getMessage()), e);
        }
    }

    /**
     * 配置TLS
     *
     * @param builder      NettyChannelBuilder
     * @param serviceProps 服务配置
     */
    private void configureTls(NettyChannelBuilder builder, GrpcClientProperties.ServiceProperties serviceProps)
            throws SSLException {
        if (serviceProps.getTlsCertPath() != null) {
            File certFile = new File(serviceProps.getTlsCertPath());
            if (certFile.exists()) {
                builder.sslContext(GrpcSslContexts.forClient()
                        .trustManager(certFile)
                        .build());
                log.info("TLS enabled with custom certificate: {}", serviceProps.getTlsCertPath());
            } else {
                throw new GrpcBridgeException("TLS_CERT_NOT_FOUND",
                        "TLS certificate file not found: " + serviceProps.getTlsCertPath());
            }
        } else {
            builder.useTransportSecurity();
            log.info("TLS enabled with default trust manager");
        }
    }

    /**
     * 关闭指定服务的通道
     *
     * @param serviceName 服务名
     */
    public void closeChannel(String serviceName) {
        ManagedChannel channel = channelCache.remove(serviceName);
        if (channel != null && !channel.isShutdown()) {
            try {
                channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
                log.info("Closed gRPC channel for service: {}", serviceName);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.warn("Interrupted while closing channel for service: {}", serviceName);
            }
        }
        channelRefCount.remove(serviceName);
    }

    /**
     * 获取指定服务的空闲时间
     *
     * @param serviceName 服务名
     * @return 空闲时长，如果通道不存在则返回null
     */
    public Duration getIdleTime(String serviceName) {
        ManagedChannel channel = channelCache.get(serviceName);
        if (channel == null) {
            return null;
        }
        AtomicInteger refCount = channelRefCount.get(serviceName);
        if (refCount != null && refCount.get() == 0) {
            return properties.getPool().getMaxIdleTime();
        }
        return Duration.ZERO;
    }

    /**
     * 检查通道是否健康
     *
     * @param serviceName 服务名
     * @return true表示通道可用
     */
    public boolean isChannelHealthy(String serviceName) {
        ManagedChannel channel = channelCache.get(serviceName);
        return channel != null && !channel.isShutdown() && !channel.isTerminated();
    }

    /**
     * 获取当前活跃连接数
     *
     * @return 活跃连接数
     */
    public int getActiveChannelCount() {
        return channelCache.size();
    }

    /**
     * Spring Bean销毁时关闭所有通道和事件循环组
     */
    @PreDestroy
    public void shutdown() {
        log.info("Shutting down gRPC channel factory...");

        for (String serviceName : channelCache.keySet()) {
            closeChannel(serviceName);
        }

        eventLoopGroup.shutdownGracefully();
        try {
            eventLoopGroup.awaitTermination(10, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("Interrupted while shutting down event loop group");
        }

        log.info("gRPC channel factory shutdown complete");
    }
}
