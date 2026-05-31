package com.distributed.lock.zookeeper;

import org.apache.curator.framework.CuratorFramework;

public class ZkLockFactory {

    private final CuratorFramework curatorFramework;
    private final String applicationName;

    public ZkLockFactory(CuratorFramework curatorFramework, String applicationName) {
        this.curatorFramework = curatorFramework;
        this.applicationName = applicationName;
    }

    public ZkDistributedLock getLock(String lockKey) {
        return new ZkDistributedLock(lockKey, applicationName, curatorFramework);
    }
}