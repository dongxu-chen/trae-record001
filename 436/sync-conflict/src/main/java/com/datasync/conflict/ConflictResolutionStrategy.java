package com.datasync.conflict;

import com.datasync.common.model.ConflictResult;
import com.datasync.common.model.DataChangeEvent;

public interface ConflictResolutionStrategy {
    ConflictResult resolve(DataChangeEvent incomingEvent, DataChangeEvent existingEvent);

    String getStrategyName();
}
