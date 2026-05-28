package com.datasync.conflict;

import com.datasync.common.model.ConflictResult;
import com.datasync.common.model.DataChangeEvent;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class HlcVersionStrategy implements ConflictResolutionStrategy {

    @Override
    public ConflictResult resolve(DataChangeEvent incomingEvent, DataChangeEvent existingEvent) {
        if (existingEvent == null) {
            return ConflictResult.noConflict();
        }

        log.debug("Resolving conflict using HLC+Version strategy: incomingEventId={}, existingEventId={}",
                incomingEvent.getEventId(), existingEvent.getEventId());

        ConflictResult versionResult = resolveByBusinessVersion(incomingEvent, existingEvent);
        if (versionResult.isHasConflict() || versionResult.getConflictReason() != null) {
            return versionResult;
        }

        return resolveByHlc(incomingEvent, existingEvent);
    }

    private ConflictResult resolveByBusinessVersion(DataChangeEvent incomingEvent, DataChangeEvent existingEvent) {
        Long incomingVersion = incomingEvent.getBusinessVersion();
        Long existingVersion = existingEvent.getBusinessVersion();

        if (incomingVersion == null && existingVersion == null) {
            return ConflictResult.noConflict();
        }

        if (incomingVersion == null) {
            log.debug("Incoming event has no version, existing event wins: incomingEventId={}, existingEventId={}, existingVersion={}",
                    incomingEvent.getEventId(), existingEvent.getEventId(), existingVersion);
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Existing event has business version, incoming has none")
                    .winnerEventId(existingEvent.getEventId())
                    .loserEventId(incomingEvent.getEventId())
                    .winnerTimestamp(existingVersion)
                    .build();
        }

        if (existingVersion == null) {
            log.debug("Existing event has no version, incoming event wins: incomingEventId={}, incomingVersion={}, existingEventId={}",
                    incomingEvent.getEventId(), incomingVersion, existingEvent.getEventId());
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Incoming event has business version, existing has none")
                    .winnerEventId(incomingEvent.getEventId())
                    .loserEventId(existingEvent.getEventId())
                    .winnerTimestamp(incomingVersion)
                    .build();
        }

        if (incomingVersion > existingVersion) {
            log.debug("Incoming event has higher business version: incomingEventId={}, incomingVersion={}, existingEventId={}, existingVersion={}",
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
            log.debug("Existing event has higher business version: incomingEventId={}, incomingVersion={}, existingEventId={}, existingVersion={}",
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
        }

        log.debug("Business versions are equal, falling back to HLC comparison");
        return ConflictResult.noConflict();
    }

    private ConflictResult resolveByHlc(DataChangeEvent incomingEvent, DataChangeEvent existingEvent) {
        int hlcCompare = incomingEvent.compareHlc(existingEvent);

        if (hlcCompare > 0) {
            log.debug("Incoming event has higher HLC: incomingEventId={}, incomingHlc={}, existingEventId={}, existingHlc={}",
                    incomingEvent.getEventId(), incomingEvent.getHlcKey(), existingEvent.getEventId(), existingEvent.getHlcKey());
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Incoming event has higher HLC (logical clock)")
                    .winnerEventId(incomingEvent.getEventId())
                    .loserEventId(existingEvent.getEventId())
                    .build();
        } else if (hlcCompare < 0) {
            log.debug("Existing event has higher HLC: incomingEventId={}, incomingHlc={}, existingEventId={}, existingHlc={}",
                    incomingEvent.getEventId(), incomingEvent.getHlcKey(), existingEvent.getEventId(), existingEvent.getHlcKey());
            return ConflictResult.builder()
                    .hasConflict(true)
                    .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                    .conflictReason("Existing event has higher HLC (logical clock)")
                    .winnerEventId(existingEvent.getEventId())
                    .loserEventId(incomingEvent.getEventId())
                    .build();
        } else {
            if (incomingEvent.getEventId().compareTo(existingEvent.getEventId()) > 0) {
                log.debug("HLC are equal, using eventId as tiebreaker: incomingEventId={}, existingEventId={}",
                        incomingEvent.getEventId(), existingEvent.getEventId());
                return ConflictResult.builder()
                        .hasConflict(true)
                        .resolution(ConflictResult.ConflictResolution.APPLY_NEWER)
                        .conflictReason("HLC equal, eventId tiebreaker")
                        .winnerEventId(incomingEvent.getEventId())
                        .loserEventId(existingEvent.getEventId())
                        .build();
            }
            return ConflictResult.noConflict();
        }
    }

    @Override
    public String getStrategyName() {
        return "HLC_VERSION";
    }
}
