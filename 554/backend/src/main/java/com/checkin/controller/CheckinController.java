package com.checkin.controller;

import com.checkin.common.Result;
import com.checkin.dto.CheckinCalendarVO;
import com.checkin.dto.CheckinDTO;
import com.checkin.dto.RecheckDTO;
import com.checkin.service.CheckinService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.Map;

@RestController
@RequestMapping("/api/checkin")
public class CheckinController {

    @Autowired
    private CheckinService checkinService;

    @PostMapping
    public Result<Map<String, Object>> doCheckin(@RequestBody CheckinDTO dto) {
        try {
            Map<String, Object> result = checkinService.doCheckin(dto.getUserId(), dto.getPeriodType());
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/calendar")
    public Result<CheckinCalendarVO> getCalendar(
            @RequestParam Long userId,
            @RequestParam String periodType,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        try {
            CheckinCalendarVO calendar = checkinService.getCalendar(userId, periodType, date);
            return Result.success(calendar);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/recheck")
    public Result<Map<String, Object>> recheck(@RequestBody RecheckDTO dto) {
        try {
            Map<String, Object> result = checkinService.recheck(
                    dto.getUserId(), dto.getPeriodType(), dto.getCheckinDate());
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/treasure/{treasureId}")
    public Result<Map<String, Object>> claimTreasure(
            @PathVariable Long treasureId,
            @RequestParam Long userId) {
        try {
            Map<String, Object> result = checkinService.claimTreasure(userId, treasureId);
            return Result.success(result);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }

    @GetMapping("/stats")
    public Result<Map<String, Object>> getStats(@RequestParam Long userId) {
        try {
            Map<String, Object> stats = checkinService.getStats(userId);
            return Result.success(stats);
        } catch (Exception e) {
            return Result.error(e.getMessage());
        }
    }
}
