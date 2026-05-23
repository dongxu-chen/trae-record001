package com.meeting.booking.controller;

import com.meeting.booking.common.Result;
import com.meeting.booking.dto.CalendarViewDTO;
import com.meeting.booking.service.CalendarService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/calendar")
public class CalendarController {

    @Autowired
    private CalendarService calendarService;

    @GetMapping
    public Result<CalendarViewDTO> getCalendarView(
            @RequestParam int year,
            @RequestParam int month,
            @RequestParam(required = false) Long roomId) {
        return Result.success(calendarService.getCalendarView(year, month, roomId));
    }
}
