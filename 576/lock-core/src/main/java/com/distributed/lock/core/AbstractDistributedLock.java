package com.distributed.lock.core;

import java.net.InetAddress;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

public abstract class AbstractDistributedLock implements DistributedLock {

    protected final String lockKey;
    protected final String applicationName;
    protected final String hostName;
    protected final String ownerId;
    protected final List<LockEventListener> eventListeners = new ArrayList<>();

    protected AbstractDistributedLock(String lockKey, String applicationName) {
        this.lockKey = lockKey;
        this.applicationName = applicationName;
        this.ownerId = UUID.randomUUID().toString();
        String host = "unknown";
        try {
            host = InetAddress.getLocalHost().getHostName();
        } catch (Exception e) {
        }
        this.hostName = host;
    }

    public void addEventListener(LockEventListener listener) {
        if (listener != null) {
            this.eventListeners.add(listener);
        }
    }

    public void removeEventListener(LockEventListener listener) {
        this.eventListeners.remove(listener);
    }

    protected void publishEvent(LockEvent event) {
        for (LockEventListener listener : eventListeners) {
            try {
                listener.onEvent(event);
            } catch (Exception e) {
            }
        }
    }

    protected LockEvent buildEvent(LockEvent.EventType eventType, boolean success, Long waitTimeMs, Long holdTimeMs) {
        Thread currentThread = Thread.currentThread();
        return LockEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .lockKey(lockKey)
                .lockType(getLockType())
                .eventType(eventType)
                .threadId(String.valueOf(currentThread.getId()))
                .threadName(currentThread.getName())
                .hostName(hostName)
                .applicationName(applicationName)
                .timestamp(System.currentTimeMillis())
                .waitTimeMs(waitTimeMs)
                .holdTimeMs(holdTimeMs)
                .success(success)
                .ownerId(ownerId)
                .build();
    }

    @Override
    public boolean tryLock(long waitTime, long leaseTime, TimeUnit unit) throws InterruptedException {
        long startTime = System.currentTimeMillis();
        publishEvent(buildEvent(LockEvent.EventType.ACQUIRE_START, true, null, null));
        try {
            boolean result = doTryLock(waitTime, leaseTime, unit);
            long waitTimeMs = System.currentTimeMillis() - startTime;
            if (result) {
                publishEvent(buildEvent(LockEvent.EventType.ACQUIRE_SUCCESS, true, waitTimeMs, null));
            } else {
                publishEvent(buildEvent(LockEvent.EventType.ACQUIRE_FAIL, false, waitTimeMs, null));
            }
            return result;
        } catch (InterruptedException e) {
            long waitTimeMs = System.currentTimeMillis() - startTime;
            publishEvent(buildEvent(LockEvent.EventType.ACQUIRE_FAIL, false, waitTimeMs, null));
            throw e;
        } catch (Exception e) {
            long waitTimeMs = System.currentTimeMillis() - startTime;
            LockEvent event = buildEvent(LockEvent.EventType.ACQUIRE_FAIL, false, waitTimeMs, null);
            event.setErrorMessage(e.getMessage());
            publishEvent(event);
            throw e;
        }
    }

    @Override
    public void lock(long leaseTime, TimeUnit unit) {
        publishEvent(buildEvent(LockEvent.EventType.ACQUIRE_START, true, null, null));
        try {
            doLock(leaseTime, unit);
            publishEvent(buildEvent(LockEvent.EventType.ACQUIRE_SUCCESS, true, null, null));
        } catch (Exception e) {
            LockEvent event = buildEvent(LockEvent.EventType.ACQUIRE_FAIL, false, null, null);
            event.setErrorMessage(e.getMessage());
            publishEvent(event);
            throw e;
        }
    }

    @Override
    public void unlock() {
        publishEvent(buildEvent(LockEvent.EventType.RELEASE_START, true, null, null));
        try {
            doUnlock();
            publishEvent(buildEvent(LockEvent.EventType.RELEASE_SUCCESS, true, null, null));
        } catch (Exception e) {
            LockEvent event = buildEvent(LockEvent.EventType.RELEASE_FAIL, false, null, null);
            event.setErrorMessage(e.getMessage());
            publishEvent(event);
            throw e;
        }
    }

    protected abstract boolean doTryLock(long waitTime, long leaseTime, TimeUnit unit) throws InterruptedException;

    protected abstract void doLock(long leaseTime, TimeUnit unit);

    protected abstract void doUnlock();

    @Override
    public String getLockKey() {
        return lockKey;
    }
}