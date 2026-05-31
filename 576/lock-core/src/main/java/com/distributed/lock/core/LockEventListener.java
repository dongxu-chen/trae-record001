package com.distributed.lock.core;

public interface LockEventListener {

    void onEvent(LockEvent event);
}