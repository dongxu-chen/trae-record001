package com.tracking.flink.function;

import com.tracking.common.model.SessionInfo;
import com.tracking.common.model.TrackEvent;
import org.apache.flink.streaming.api.functions.windowing.WindowFunction;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class SessionWindowFunction implements WindowFunction<SessionInfo, SessionInfo, String, TimeWindow> {

    private static final Logger LOG = LoggerFactory.getLogger(SessionWindowFunction.class);

    @Override
    public void apply(String sessionId, TimeWindow window, Iterable<SessionInfo> input, Collector<SessionInfo> out) {
        for (SessionInfo session : input) {
            if (session.getEndTime() == null) {
                session.setEndTime(window.getEnd());
            }
            if (session.getSessionId() == null) {
                session.setSessionId(sessionId);
            }
            LOG.debug("Session aggregated: {}, events: {}, duration: {}ms",
                    sessionId, session.getEventCount(),
                    session.getEndTime() - session.getStartTime());
            out.collect(session);
        }
    }
}
