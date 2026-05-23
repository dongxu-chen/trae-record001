package com.distributed.lock.examples;

import com.distributed.lock.server.LockServer;
import com.distributed.lock.server.config.LockServerConfig;

import java.util.Arrays;

public class ServerExample {
    public static void main(String[] args) throws Exception {
        LockServerConfig config = LockServerConfig.builder()
                .etcdEndpoints(Arrays.asList("http://localhost:2379"))
                .grpcPort(50051)
                .defaultLeaseTtlSeconds(30)
                .leaseAutoRenewEnabled(true)
                .leaseRenewIntervalSeconds(10)
                .build();
        
        LockServer server = new LockServer(config);
        server.start();
        System.out.println("Distributed Lock Server started on port 50051");
        System.out.println("Press Ctrl+C to stop...");
        server.blockUntilShutdown();
    }
}