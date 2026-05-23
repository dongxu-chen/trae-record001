package com.meeting.booking.controller;

import com.meeting.booking.common.Result;
import com.meeting.booking.dto.RoomUsageStatsDTO;
import com.meeting.booking.dto.StatisticsQueryDTO;
import com.meeting.booking.service.StatisticsService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/statistics")
public class StatisticsController {

    @Autowired
    private StatisticsService statisticsService;

    @GetMapping("/room-usage")
    public Result<List<RoomUsageStatsDTO>> getRoomUsageStatistics(StatisticsQueryDTO query) {
        return Result.success(statisticsService.getRoomUsageStatistics(query));
    }
}
