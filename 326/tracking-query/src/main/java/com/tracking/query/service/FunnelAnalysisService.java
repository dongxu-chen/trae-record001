package com.tracking.query.service;

import com.tracking.common.constant.TrackingConstants;
import com.tracking.common.model.FunnelQuery;
import com.tracking.common.model.FunnelResult;
import com.tracking.storage.dao.FunnelDao;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class FunnelAnalysisService {

    private static final Logger LOG = LoggerFactory.getLogger(FunnelAnalysisService.class);

    private final FunnelDao funnelDao;

    public FunnelAnalysisService(FunnelDao funnelDao) {
        this.funnelDao = funnelDao;
    }

    public FunnelResult calculateFunnel(FunnelQuery query) {
        if (query.getEvents() == null || query.getEvents().size() < 2) {
            throw new IllegalArgumentException("漏斗分析至少需要2个事件步骤");
        }

        if (query.getStartTime() == null || query.getEndTime() == null) {
            throw new IllegalArgumentException("必须指定开始和结束时间");
        }

        if (query.getWindowMinutes() == null) {
            query.setWindowMinutes(60);
        }

        if (Boolean.TRUE.equals(query.getSlidingWindow())) {
            validateSlidingWindowParams(query);
        }

        LOG.info("Calculating funnel: {}, events: {}, window: {} minutes, sliding: {}",
                query.getFunnelName(), query.getEvents(), query.getWindowMinutes(),
                query.getSlidingWindow());

        if (Boolean.TRUE.equals(query.getSlidingWindow())) {
            LOG.info("Sliding window params: unit={}, size={}, step={}",
                    query.getSlidingWindowUnit(), query.getSlidingWindowSize(),
                    query.getSlidingWindowStep());
        }

        FunnelResult result = funnelDao.calculateFunnel(query);

        LOG.info("Funnel result: totalUsers={}, steps={}", result.getTotalUsers(),
                result.getSteps() != null ? result.getSteps().size() : 0);

        if (Boolean.TRUE.equals(result.getSlidingWindow()) && result.getSlidingWindowResults() != null) {
            LOG.info("Sliding window results count: {}", result.getSlidingWindowResults().size());
        }

        return result;
    }

    private void validateSlidingWindowParams(FunnelQuery query) {
        String unit = query.getSlidingWindowUnit();
        if (unit == null) {
            query.setSlidingWindowUnit(TrackingConstants.FUNNEL_WINDOW_DAILY);
        }

        if (!TrackingConstants.FUNNEL_WINDOW_HOURLY.equals(unit) &&
            !TrackingConstants.FUNNEL_WINDOW_DAILY.equals(unit) &&
            !TrackingConstants.FUNNEL_WINDOW_WEEKLY.equals(unit) &&
            !TrackingConstants.FUNNEL_WINDOW_CUSTOM.equals(unit)) {
            throw new IllegalArgumentException(
                "无效的滑动窗口单位，必须是: hourly, daily, weekly, custom");
        }

        if (query.getSlidingWindowSize() == null || query.getSlidingWindowSize() <= 0) {
            query.setSlidingWindowSize(1);
        }

        long timeRange = query.getEndTime() - query.getStartTime();
        long windowSizeMillis = calculateWindowSizeMillis(query);

        if (windowSizeMillis > timeRange) {
            throw new IllegalArgumentException("滑动窗口大小不能超过时间范围");
        }

        long minWindowSize = 60 * 60 * 1000L;
        if (windowSizeMillis < minWindowSize) {
            throw new IllegalArgumentException("滑动窗口大小不能小于1小时");
        }
    }

    private long calculateWindowSizeMillis(FunnelQuery query) {
        String unit = query.getSlidingWindowUnit();
        int size = query.getSlidingWindowSize() != null ? query.getSlidingWindowSize() : 1;

        switch (unit) {
            case TrackingConstants.FUNNEL_WINDOW_HOURLY:
                return size * 60 * 60 * 1000L;
            case TrackingConstants.FUNNEL_WINDOW_DAILY:
                return size * 24 * 60 * 60 * 1000L;
            case TrackingConstants.FUNNEL_WINDOW_WEEKLY:
                return size * 7 * 24 * 60 * 60 * 1000L;
            case TrackingConstants.FUNNEL_WINDOW_CUSTOM:
            default:
                return size * 60 * 1000L;
        }
    }

    public FunnelResult calculatePurchaseFunnel(Long startTime, Long endTime,
                                                String platform, String appId) {
        FunnelQuery query = FunnelQuery.builder()
                .funnelName("购买转化漏斗")
                .events(List.of("page_view", "add_to_cart", "purchase"))
                .startTime(startTime)
                .endTime(endTime)
                .windowMinutes(60 * 24)
                .platform(platform)
                .appId(appId)
                .build();
        return calculateFunnel(query);
    }

    public FunnelResult calculateRegistrationFunnel(Long startTime, Long endTime,
                                                    String platform, String appId) {
        FunnelQuery query = FunnelQuery.builder()
                .funnelName("注册转化漏斗")
                .events(List.of("page_view", "register", "login"))
                .startTime(startTime)
                .endTime(endTime)
                .windowMinutes(60 * 24)
                .platform(platform)
                .appId(appId)
                .build();
        return calculateFunnel(query);
    }
}
