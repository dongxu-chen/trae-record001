package com.datasync.conflict;

import com.datasync.common.model.ConflictResult;
import com.datasync.common.model.DataChangeEvent;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class TimestampBasedStrategy implements ConflictResolutionStrategy {
    @Override
    public ConflictResult resolve(DataChangeEvent incomingEvent, DataChangeEvent existingEvent) {
        if (existingEvent == null) {
            return ConflictResult.noConflict();
        }

        long incomingTimestamp = getEventTimestamp(incomingEvent);
        long existingTimestamp = getEventTimestamp(existingEvent);

        if (incomingTimestamp > existingTimestamp) {
            log.debug("Incoming event is newer: incomingEventId={}, incomingTimestamp={}, existingEventId={}, existingTimestamp={}",
                    incomingEvent.getEventId(), incomingTimestamp, existingEvent.getEventId(), existingTimestamp);
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Incoming event has newer timestamp")
                    .winnerEventId(incomingEvent.getEventId())
                    .loserEventId(existingEvent.getEventId())
                    .winnerTimestamp(incomingTimestamp)
                    .loserTimestamp(existingTimestamp)
                    .build();
        } else if (incomingTimestamp < existingTimestamp) {
            log.debug("Existing event is newer: incomingEventId={}, incomingTimestamp={}, existingEventId={}, existingTimestamp={}",
                    incomingEvent.getEventId(), incomingTimestamp, existingEvent.getEventId(), existingTimestamp);
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Existing event has newer timestamp")
                    .winnerEventId(existingEvent.getEventId())
                    .loserEventId(incomingEvent.getEventId())
                    .winnerTimestamp(existingTimestamp)
                    .loserTimestamp(incomingTimestamp)
                    .build();
        } else {
            if (incomingEvent.getEventId().compareTo(existingEvent.getEventId()) > 0) {
                log.debug("Timestamps are equal, using eventId as tiebreaker: incomingEventId={}, existingEventId={}",
                        incomingEvent.getEventId(), existingEvent.getEventId());
                return ConflictResult.builder()
                        .hasConflict(true)
                        .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                        .conflictReason("Timestamps equal, eventId tiebreaker")
                        .winnerEventId(incomingEvent.getEventId())
                        .loserEventId(existingEvent.getEventId())
                        .winnerTimestamp(incomingTimestamp)
                        .loserTimestamp(existingTimestamp)
                        .build();
            }
            return ConflictResult.noConflict();
        }
    }

    private long getEventTimestamp(DataChangeEvent event) {
        if (event.getExecutionTime() != null && event.getExecutionTime() > 0) {
            return event.getExecutionTime();
        }
        if (event.getTimestamp() != null) {
            return event.getTimestamp();
        }
        return 0L;
    }

    @Override
    public String getStrategyName() {
        return "TIMESTAMP_BASED";
    }
}
