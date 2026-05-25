package com.tracking.query.service;

import com.tracking.common.model.ClickStreamQuery;
import com.tracking.common.model.ClickStreamResult;
import com.tracking.common.model.TrackEvent;
import com.tracking.storage.dao.EventDao;
import com.tracking.storage.service.UserMappingService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ClickStreamService {

    private static final Logger LOG = LoggerFactory.getLogger(ClickStreamService.class);

    private final EventDao eventDao;
    private final UserMappingService userMappingService;

    public ClickStreamService(EventDao eventDao, UserMappingService userMappingService) {
        this.eventDao = eventDao;
        this.userMappingService = userMappingService;
    }

    public ClickStreamResult queryClickStream(ClickStreamQuery query) {
        if (query.getUserId() == null && query.getAnonymousId() != null) {
            String mappedUserId = userMappingService.getUserId(query.getAnonymousId());
            if (mappedUserId != null) {
                query.setUserId(mappedUserId);
            }
        }

        if (query.getUserId() == null && query.getDeviceId() != null) {
            String anonymousId = userMappingService.getAnonymousIdByDevice(query.getDeviceId());
            if (anonymousId != null) {
                String mappedUserId = userMappingService.getUserId(anonymousId);
                if (mappedUserId != null) {
                    query.setUserId(mappedUserId);
                } else {
                    query.setAnonymousId(anonymousId);
                }
            }
        }

        ClickStreamResult result = eventDao.queryClickStream(query);

        enhanceWithUserMapping(result);

        return result;
    }

    public List<TrackEvent> queryUserClickStream(String userId, Long startTime, Long endTime,
                                                 Integer page, Integer pageSize) {
        ClickStreamQuery query = ClickStreamQuery.builder()
                .userId(userId)
                .startTime(startTime)
                .endTime(endTime)
                .page(page)
                .pageSize(pageSize)
                .build();
        return eventDao.queryClickStream(query).getEvents();
    }

    public List<TrackEvent> querySessionClickStream(String sessionId, Integer page, Integer pageSize) {
        ClickStreamQuery query = ClickStreamQuery.builder()
                .sessionId(sessionId)
                .page(page)
                .pageSize(pageSize)
                .build();
        return eventDao.queryClickStream(query).getEvents();
    }

    public long countActiveUsers(Long startTime, Long endTime, String platform, String appId) {
        return eventDao.countDistinctUsers(startTime, endTime, platform, appId);
    }

    private void enhanceWithUserMapping(ClickStreamResult result) {
        if (result.getEvents() == null) {
            return;
        }
        for (TrackEvent event : result.getEvents()) {
            if (event.getUserId() == null && event.getAnonymousId() != null) {
                String userId = userMappingService.getUserId(event.getAnonymousId());
                if (userId != null) {
                    event.setUserId(userId);
                }
            }
        }
    }
}
