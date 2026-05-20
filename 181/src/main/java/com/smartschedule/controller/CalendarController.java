package com.smartschedule.controller;

import com.smartschedule.dto.CalendarCell;
import com.smartschedule.dto.CalendarViewData;
import com.smartschedule.service.CalendarViewService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/calendar")
@CrossOrigin(origins = "*")
public class CalendarController {

    @Autowired
    private CalendarViewService calendarViewService;

    @GetMapping("/schedule/{scheduleId}")
    public ResponseEntity<CalendarViewData> getCalendarView(@PathVariable Long scheduleId) {
        return ResponseEntity.ok(calendarViewService.getCalendarView(scheduleId));
    }

    @GetMapping("/validate/{assignmentId}")
    public ResponseEntity<CalendarCell> validateAssignmentChange(
            @PathVariable Long assignmentId,
            @RequestParam(required = false) Long newEmployeeId) {
        return ResponseEntity.ok(calendarViewService.validateAssignmentChange(assignmentId, newEmployeeId));
    }
}
