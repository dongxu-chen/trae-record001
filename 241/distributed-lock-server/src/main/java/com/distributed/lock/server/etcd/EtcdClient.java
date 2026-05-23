package com.distributed.lock.server.etcd;

import com.distributed.lock.server.config.LockServerConfig;
import io.etcd.jetcd.ByteSequence;
import io.etcd.jetcd.Client;
import io.etcd.jetcd.KV;
import io.etcd.jetcd.Lease;
import io.etcd.jetcd.Watch;
import io.etcd.jetcd.kv.GetResponse;
import io.etcd.jetcd.kv.PutResponse;
import io.etcd.jetcd.lease.LeaseGrantResponse;
import io.etcd.jetcd.options.GetOption;
import io.etcd.jetcd.options.PutOption;
import io.etcd.jetcd.options.WatchOption;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

public class EtcdClient implements AutoCloseable {
    
    private static final Logger logger = LoggerFactory.getLogger(EtcdClient.class);
    
    private final Client client;
    private final KV kvClient;
    private final Lease leaseClient;
    private final Watch watchClient;
    private final LockServerConfig config;

    public EtcdClient(LockServerConfig config) {
        this.config = config;
        this.client = Client.builder()
                .endpoints(config.getEtcdEndpoints())
                .build();
        this.kvClient = client.getKVClient();
        this.leaseClient = client.getLeaseClient();
        this.watchClient = client.getWatchClient();
        logger.info("EtcdClient initialized with endpoints: {}", config.getEtcdEndpoints());
    }

    public CompletableFuture<PutResponse> put(String key, String value) {
        return kvClient.put(bytes(key), bytes(value));
    }

    public CompletableFuture<PutResponse> putWithLease(String key, String value, long leaseId) {
        PutOption option = PutOption.newBuilder()
                .withLeaseId(leaseId)
                .build();
        return kvClient.put(bytes(key), bytes(value), option);
    }

    public CompletableFuture<GetResponse> get(String key) {
        return kvClient.get(bytes(key));
    }

    public CompletableFuture<GetResponse> getWithPrefix(String prefix) {
        GetOption option = GetOption.newBuilder()
                .isPrefix(true)
                .build();
        return kvClient.get(bytes(prefix), option);
    }

    public CompletableFuture<Long> grantLease(long ttlSeconds) {
        return leaseClient.grant(ttlSeconds)
                .thenApply(LeaseGrantResponse::getID);
    }

    public void keepAliveOnce(long leaseId) {
        try {
            leaseClient.keepAliveOnce(leaseId)
                    .get(5, TimeUnit.SECONDS);
        } catch (InterruptedException | ExecutionException | TimeoutException e) {
            logger.warn("Failed to keep alive lease {}: {}", leaseId, e.getMessage());
        }
    }

    public CompletableFuture<Boolean> delete(String key) {
        return kvClient.delete(bytes(key))
                .thenApply(response -> response.getDeleted() > 0);
    }

    public Watch.Watcher watch(String key, Watch.Listener listener) {
        return watchClient.watch(bytes(key), listener);
    }

    public Watch.Watcher watchWithPrefix(String prefix, Watch.Listener listener) {
        WatchOption option = WatchOption.newBuilder()
                .isPrefix(true)
                .build();
        return watchClient.watch(bytes(prefix), option, listener);
    }

    public String getLockKey(String lockName) {
        return config.getLockPrefix() + lockName;
    }

    public static ByteSequence bytes(String s) {
        return ByteSequence.from(s, StandardCharsets.UTF_8);
    }

    public static String string(ByteSequence bs) {
        return bs.toString(StandardCharsets.UTF_8);
    }

    @Override
    public void close() {
        logger.info("Closing EtcdClient...");
        try {
            watchClient.close();
            leaseClient.close();
            kvClient.close();
            client.close();
            logger.info("EtcdClient closed successfully");
        } catch (Exception e) {
            logger.error("Error closing EtcdClient", e);
        }
    }
}