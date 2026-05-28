package com.datasync.conflict;

import com.datasync.common.model.ConflictResult;
import com.datasync.common.model.DataChangeEvent;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class BusinessVersionStrategy implements ConflictResolutionStrategy {
    @Override
    public ConflictResult resolve(DataChangeEvent incomingEvent, DataChangeEvent existingEvent) {
        if (existingEvent == null) {
            return ConflictResult.noConflict();
        }

        Long incomingVersion = incomingEvent.getBusinessVersion();
        Long existingVersion = existingEvent.getBusinessVersion();

        if (incomingVersion == null && existingVersion == null) {
            return resolveWithTimestampFallback(incomingEvent, existingEvent);
        }

        if (incomingVersion == null) {
            log.debug("Incoming event has no version, existing event wins: incomingEventId={}, existingEventId={}, existingVersion={}",
                    incomingEvent.getEventId(), existingEvent.getEventId(), existingVersion);
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Existing event has version, incoming has none")
                    .winnerEventId(existingEvent.getEventId())
                    .loserEventId(incomingEvent.getEventId())
                    .build();
        }

        if (existingVersion == null) {
            log.debug("Existing event has no version, incoming event wins: incomingEventId={}, incomingVersion={}, existingEventId={}",
                    incomingEvent.getEventId(), incomingVersion, existingEvent.getEventId());
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Incoming event has version, existing has none")
                    .winnerEventId(incomingEvent.getEventId())
                    .loserEventId(existingEvent.getEventId())
                    .build();
        }

        if (incomingVersion > existingVersion) {
            log.debug("Incoming event has higher version: incomingEventId={}, incomingVersion={}, existingEventId={}, existingVersion={}",
                    incomingEvent.getEventId(), incomingVersion, existingEvent.getEventId(), existingVersion);
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Incoming event has higher business version")
                    .winnerEventId(incomingEvent.getEventId())
                    .loserEventId(existingEvent.getEventId())
                    .winnerTimestamp(incomingVersion)
                    .loserTimestamp(existingVersion)
                    .build();
        } else if (incomingVersion < existingVersion) {
            log.debug("Existing event has higher version: incomingEventId={}, incomingVersion={}, existingEventId={}, existingVersion={}",
                    incomingEvent.getEventId(), incomingVersion, existingEvent.getEventId(), existingVersion);
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Existing event has higher business version")
                    .winnerEventId(existingEvent.getEventId())
                    .loserEventId(incomingEvent.getEventId())
                    .winnerTimestamp(existingVersion)
                    .loserTimestamp(incomingVersion)
                    .build();
        } else {
            return resolveWithTimestampFallback(incomingEvent, existingEvent);
        }
    }

    private ConflictResult resolveWithTimestampFallback(DataChangeEvent incomingEvent, DataChangeEvent existingEvent) {
        TimestampBasedStrategy timestampStrategy = new TimestampBasedStrategy();
        ConflictResult result = timestampStrategy.resolve(incomingEvent, existingEvent);

        if (result.isHasConflict()) {
            result.setConflictReason("Business versions equal, falling back to timestamp comparison: " + result.getConflictReason());
        }
        return result;
    }

    @Override
    public String getStrategyName() {
        return "BUSINESS_VERSION";
    }
}
