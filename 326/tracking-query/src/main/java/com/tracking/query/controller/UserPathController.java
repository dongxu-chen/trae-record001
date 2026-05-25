package com.tracking.query.controller;

import com.tracking.common.model.SankeyPath;
import com.tracking.common.model.UserPathQuery;
import com.tracking.common.response.ApiResponse;
import com.tracking.storage.dao.UserPathDao;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/path")
public class UserPathController {

    private final UserPathDao userPathDao;

    public UserPathController(UserPathDao userPathDao) {
        this.userPathDao = userPathDao;
    }

    @PostMapping("/sankey")
    public ApiResponse<SankeyPath> getSankeyPath(@RequestBody UserPathQuery query) {
        if (query.getStartTime() == null || query.getEndTime() == null) {
            return ApiResponse.error("startTime and endTime are required");
        }

        try {
            SankeyPath sankeyPath = userPathDao.getUserPathSankey(query);
            return ApiResponse.success(sankeyPath);
        } catch (Exception e) {
            return ApiResponse.error("Failed to get sankey path: " + e.getMessage());
        }
    }

    @GetMapping("/sankey")
    public ApiResponse<SankeyPath> getSankeyPathByParams(
            @RequestParam Long startTime,
            @RequestParam Long endTime,
            @RequestParam(required = false) String platform,
            @RequestParam(required = false) String appId,
            @RequestParam(required = false) String startEvent,
            @RequestParam(defaultValue = "10") Integer maxPathLength,
            @RequestParam(defaultValue = "50") Integer topN) {

        UserPathQuery query = UserPathQuery.builder()
                .startTime(startTime)
                .endTime(endTime)
                .platform(platform)
                .appId(appId)
                .startEvent(startEvent)
                .maxPathLength(maxPathLength)
                .topN(topN)
                .build();

        try {
            SankeyPath sankeyPath = userPathDao.getUserPathSankey(query);
            return ApiResponse.success(sankeyPath);
        } catch (Exception e) {
            return ApiResponse.error("Failed to get sankey path: " + e.getMessage());
        }
    }

    @PostMapping("/top")
    public ApiResponse<List<Map<String, Object>>> getTopPaths(@RequestBody UserPathQuery query) {
        if (query.getStartTime() == null || query.getEndTime() == null) {
            return ApiResponse.error("startTime and endTime are required");
        }

        try {
            List<Map<String, Object>> paths = userPathDao.getTopPaths(query);
            return ApiResponse.success(paths);
        } catch (Exception e) {
            return ApiResponse.error("Failed to get top paths: " + e.getMessage());
        }
    }
}
