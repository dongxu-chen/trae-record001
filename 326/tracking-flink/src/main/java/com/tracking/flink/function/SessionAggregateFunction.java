package com.tracking.flink.function;

import com.tracking.common.model.SessionInfo;
import com.tracking.common.model.TrackEvent;
import org.apache.flink.api.common.functions.AggregateFunction;

public class SessionAggregateFunction implements AggregateFunction<TrackEvent, SessionInfo, SessionInfo> {

    @Override
    public SessionInfo createAccumulator() {
        return new SessionInfo();
    }

    @Override
    public SessionInfo add(TrackEvent event, SessionInfo accumulator) {
        if (accumulator.getSessionId() == null) {
            return SessionInfo.create(event);
        } else {
            accumulator.update(event);
            return accumulator;
        }
    }

    @Override
    public SessionInfo getResult(SessionInfo accumulator) {
        return accumulator;
    }

    @Override
    public SessionInfo merge(SessionInfo a, SessionInfo b) {
        if (a.getStartTime() == null) {
            return b;
        }
        if (b.getStartTime() == null) {
            return a;
        }

        SessionInfo merged = new SessionInfo();
        merged.setSessionId(a.getSessionId());
        merged.setAnonymousId(a.getAnonymousId() != null ? a.getAnonymousId() : b.getAnonymousId());
        merged.setUserId(a.getUserId() != null ? a.getUserId() : b.getUserId());
        merged.setDeviceId(a.getDeviceId() != null ? a.getDeviceId() : b.getDeviceId());
        merged.setStartTime(Math.min(a.getStartTime(), b.getStartTime()));
        merged.setEndTime(Math.max(a.getEndTime(), b.getEndTime()));
        merged.setEventCount((a.getEventCount() != null ? a.getEventCount() : 0) +
                (b.getEventCount() != null ? b.getEventCount() : 0));
        merged.setLastEventTime(Math.max(a.getLastEventTime(), b.getLastEventTime()));
        merged.setFirstPage(a.getFirstPage() != null ? a.getFirstPage() : b.getFirstPage());
        merged.setLastPage(b.getLastPage() != null ? b.getLastPage() : a.getLastPage());
        merged.setEntrySource(a.getEntrySource() != null ? a.getEntrySource() : b.getEntrySource());

        return merged;
    }
}
