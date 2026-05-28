package com.datasync.cdc;

import com.datasync.common.model.DataChangeEvent;

import java.util.List;
import java.util.function.Consumer;

public interface CdcConnector {
    void start();

    void stop();

    boolean isRunning();

    void registerListener(Consumer<List<DataChangeEvent>> listener);

    String getConnectorId();

    String getDatabaseId();
}
