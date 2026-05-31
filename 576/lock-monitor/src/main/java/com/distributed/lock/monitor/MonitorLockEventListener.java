package com.distributed.lock.monitor;

import com.distributed.lock.core.LockEvent;
import com.distributed.lock.core.LockEventListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class MonitorLockEventListener implements LockEventListener {

    private final LockMonitorManager monitorManager;

    @Autowired
    public MonitorLockEventListener(LockMonitorManager monitorManager) {
        this.monitorManager = monitorManager;
    }

    @Override
    public void onEvent(LockEvent event) {
        monitorManager.onLockEvent(event);
    }
}