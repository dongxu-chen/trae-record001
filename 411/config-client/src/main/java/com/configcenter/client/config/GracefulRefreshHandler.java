package com.configcenter.client.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.refresh.ContextRefresher;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import javax.annotation.PreDestroy;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Component
public class GracefulRefreshHandler {

    private static final Logger logger = LoggerFactory.getLogger(GracefulRefreshHandler.class);

    private final AtomicInteger activeRequests = new AtomicInteger(0);
    private final AtomicBoolean refreshPending = new AtomicBoolean(false);
    private final ReentrantReadWriteLock refreshLock = new ReentrantReadWriteLock();

    @Value("${config.graceful-refresh.timeout-seconds:30}")
    private int timeoutSeconds;

    @Value("${config.graceful-refresh.wait-interval-ms:100}")
    private long waitIntervalMs;

    private final ContextRefresher contextRefresher;
    private final ApplicationContext applicationContext;

    public GracefulRefreshHandler(ContextRefresher contextRefresher, ApplicationContext applicationContext) {
        this.contextRefresher = contextRefresher;
        this.applicationContext = applicationContext;
    }

    public void incrementRequest() {
        activeRequests.incrementAndGet();
    }

    public void decrementRequest() {
        activeRequests.decrementAndGet();
        checkAndRefresh();
    }

    public boolean tryAcquireReadLock() {
        if (refreshPending.get()) {
            return false;
        }
        return refreshLock.readLock().tryLock();
    }

    public void releaseReadLock() {
        try {
            refreshLock.readLock().unlock();
        } catch (IllegalMonitorStateException e) {
        }
    }

    public synchronized void triggerGracefulRefresh() {
        if (refreshPending.compareAndSet(false, true)) {
            logger.info("配置优雅刷新已触发，等待请求处理完毕...");
            new Thread(this::doGracefulRefresh).start();
        }
    }

    private void doGracefulRefresh() {
        try {
            refreshLock.writeLock().lock();
            try {
                long startTime = System.currentTimeMillis();
                long timeoutMs = timeoutSeconds * 1000L;

                while (activeRequests.get() > 0) {
                    if (System.currentTimeMillis() - startTime > timeoutMs) {
                        logger.warn("优雅刷新超时，等待{}秒后强制刷新，当前活跃请求: {}",
                                timeoutSeconds, activeRequests.get());
                        break;
                    }

                    logger.debug("等待请求处理完毕，当前活跃请求: {}", activeRequests.get());
                    Thread.sleep(waitIntervalMs);
                }

                logger.info("开始刷新配置，当前活跃请求: {}", activeRequests.get());
                contextRefresher.refresh();
                logger.info("配置刷新完成");

            } finally {
                refreshLock.writeLock().unlock();
            }
        } catch (InterruptedException e) {
            logger.warn("优雅刷新被中断");
            Thread.currentThread().interrupt();
        } catch (Exception e) {
            logger.error("优雅刷新失败", e);
        } finally {
            refreshPending.set(false);
        }
    }

    public int getActiveRequests() {
        return activeRequests.get();
    }

    public boolean isRefreshPending() {
        return refreshPending.get();
    }

    @PreDestroy
    public void destroy() {
        logger.info("应用关闭，等待请求处理完毕...");
        long startTime = System.currentTimeMillis();
        long timeoutMs = 10000;

        while (activeRequests.get() > 0) {
            if (System.currentTimeMillis() - startTime > timeoutMs) {
                logger.warn("关闭超时，强制关闭");
                break;
            }
            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }
}
