package com.ticket.controller;

import com.ticket.calendar.WorkCalendarConfig;
import com.ticket.calendar.WorkCalendarService;
import com.ticket.common.Result;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/calendar")
@RequiredArgsConstructor
public class CalendarController {

    private final WorkCalendarService calendarService;
    private final WorkCalendarConfig calendarConfig;

    @GetMapping("/config")
    public Result<WorkCalendarConfig> getConfig() {
        return Result.success(calendarConfig);
    }

    @PutMapping("/config")
    public Result<WorkCalendarConfig> updateConfig(@RequestBody WorkCalendarConfig config) {
        calendarConfig.setWorkStartTime(config.getWorkStartTime());
        calendarConfig.setWorkEndTime(config.getWorkEndTime());
        calendarConfig.setNoonStartTime(config.getNoonStartTime());
        calendarConfig.setNoonEndTime(config.getNoonEndTime());
        calendarConfig.setWorkDays(config.getWorkDays());
        calendarConfig.setEnabled(config.isEnabled());
        return Result.success(calendarConfig);
    }

    @PostMapping("/holidays")
    public Result<Void> addHoliday(@RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        calendarService.addHoliday(date);
        return Result.success();
    }

    @PostMapping("/holidays/batch")
    public Result<Void> addHolidays(@RequestBody List<@DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate> dates) {
        calendarService.addHolidays(dates);
        return Result.success();
    }

    @DeleteMapping("/holidays")
    public Result<Void> removeHoliday(@RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        calendarService.removeHoliday(date);
        return Result.success();
    }

    @GetMapping("/holidays/{year}")
    public Result<List<LocalDate>> getHolidays(@PathVariable int year) {
        return Result.success(calendarService.getHolidaysForYear(year));
    }

    @PostMapping("/workdays")
    public Result<Void> addWorkday(@RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        calendarService.addWorkday(date);
        return Result.success();
    }

    @PostMapping("/workdays/batch")
    public Result<Void> addWorkdays(@RequestBody List<@DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate> dates) {
        calendarService.addWorkdays(dates);
        return Result.success();
    }

    @DeleteMapping("/workdays")
    public Result<Void> removeWorkday(@RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        calendarService.removeWorkday(date);
        return Result.success();
    }

    @GetMapping("/workdays/{year}")
    public Result<List<LocalDate>> getWorkdays(@PathVariable int year) {
        return Result.success(calendarService.getWorkdaysForYear(year));
    }

    @GetMapping("/check-workday")
    public Result<Map<String, Object>> checkWorkday(@RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate date) {
        Map<String, Object> result = new HashMap<>();
        result.put("date", date);
        result.put("isWorkday", calendarService.isWorkday(date));
        result.put("isHoliday", calendarService.isHoliday(date));
        result.put("isExtraWorkday", calendarService.isExtraWorkday(date));
        return Result.success(result);
    }

    @GetMapping("/check-worktime")
    public Result<Map<String, Object>> checkWorktime(@RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime time) {
        Map<String, Object> result = new HashMap<>();
        result.put("time", time);
        result.put("isWorkTime", calendarService.isWorkTime(time));
        result.put("isWorkday", calendarService.isWorkday(time.toLocalDate()));
        return Result.success(result);
    }

    @GetMapping("/calculate-deadline")
    public Result<Map<String, Object>> calculateDeadline(
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam int workMinutes) {
        LocalDateTime deadline = calendarService.calculateDeadline(startTime, workMinutes);
        Map<String, Object> result = new HashMap<>();
        result.put("startTime", startTime);
        result.put("workMinutes", workMinutes);
        result.put("deadline", deadline);
        result.put("actualMinutes", calendarService.calculateWorkMinutes(startTime, deadline));
        return Result.success(result);
    }

    @GetMapping("/calculate-work-minutes")
    public Result<Map<String, Object>> calculateWorkMinutes(
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime start,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime end) {
        long workMinutes = calendarService.calculateWorkMinutes(start, end);
        Map<String, Object> result = new HashMap<>();
        result.put("start", start);
        result.put("end", end);
        result.put("workMinutes", workMinutes);
        result.put("workHours", workMinutes / 60.0);
        return Result.success(result);
    }
}
