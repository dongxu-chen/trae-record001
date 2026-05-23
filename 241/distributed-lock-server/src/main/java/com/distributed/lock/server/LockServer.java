package com.distributed.lock.server;

import com.distributed.lock.server.config.LockServerConfig;
import com.distributed.lock.server.etcd.EtcdClient;
import com.distributed.lock.server.grpc.LockMonitorServiceImpl;
import com.distributed.lock.server.grpc.LockServiceImpl;
import com.distributed.lock.server.lock.LockManager;
import io.grpc.Server;
import io.grpc.ServerBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;

public class LockServer {
    
    private static final Logger logger = LoggerFactory.getLogger(LockServer.class);
    
    private final LockServerConfig config;
    private final EtcdClient etcdClient;
    private final LockManager lockManager;
    private final Server server;

    public LockServer(LockServerConfig config) {
        this.config = config;
        this.etcdClient = new EtcdClient(config);
        this.lockManager = new LockManager(etcdClient, config);
        
        this.server = ServerBuilder.forPort(config.getGrpcPort())
                .addService(new LockServiceImpl(lockManager))
                .addService(new LockMonitorServiceImpl(lockManager))
                .build();
        
        logger.info("LockServer initialized on port {}", config.getGrpcPort());
    }

    public void start() throws IOException {
        server.start();
        logger.info("LockServer started successfully on port {}", config.getGrpcPort());
        
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("Shutting down LockServer...");
            LockServer.this.stop();
            logger.info("LockServer shut down");
        }));
    }

    public void stop() {
        if (server != null) {
            server.shutdown();
        }
        if (lockManager != null) {
            lockManager.close();
        }
        if (etcdClient != null) {
            etcdClient.close();
        }
    }

    public void blockUntilShutdown() throws InterruptedException {
        if (server != null) {
            server.awaitTermination();
        }
    }

    public static void main(String[] args) throws Exception {
        String etcdEndpoints = System.getenv("ETCD_ENDPOINTS");
        String grpcPortStr = System.getenv("GRPC_PORT");
        String leaseTtlStr = System.getenv("LEASE_TTL_SECONDS");
        
        LockServerConfig.Builder configBuilder = LockServerConfig.builder();
        
        if (etcdEndpoints != null && !etcdEndpoints.isEmpty()) {
            List<String> endpoints = Arrays.asList(etcdEndpoints.split(","));
            configBuilder.etcdEndpoints(endpoints);
        }
        
        if (grpcPortStr != null && !grpcPortStr.isEmpty()) {
            configBuilder.grpcPort(Integer.parseInt(grpcPortStr));
        }
        
        if (leaseTtlStr != null && !leaseTtlStr.isEmpty()) {
            configBuilder.defaultLeaseTtlSeconds(Long.parseLong(leaseTtlStr));
        }
        
        LockServerConfig config = configBuilder.build();
        LockServer server = new LockServer(config);
        server.start();
        server.blockUntilShutdown();
    }
}