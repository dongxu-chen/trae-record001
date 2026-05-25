package com.taskscheduler.admin.controller;

import com.taskscheduler.common.dto.GanttTaskDTO;
import com.taskscheduler.common.dto.Result;
import com.taskscheduler.core.service.GanttService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/gantt")
public class GanttController {

    @Autowired
    private GanttService ganttService;

    @GetMapping("/data")
    public Result<List<GanttTaskDTO>> getGanttData(
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime,
            @RequestParam(required = false) String taskGroup,
            @RequestParam(required = false) Long taskId) {

        if (startTime == null) {
            startTime = LocalDateTime.now().minusHours(24);
        }
        if (endTime == null) {
            endTime = LocalDateTime.now().plusHours(1);
        }

        return Result.success(ganttService.getGanttData(startTime, endTime, taskGroup, taskId));
    }

    @GetMapping("/data/{logId}")
    public Result<List<GanttTaskDTO>> getGanttDataByLogId(@PathVariable Long logId) {
        return Result.success(ganttService.getGanttDataByLogId(logId));
    }

    @GetMapping("/stats")
    public Result<Map<String, Object>> getGanttStats(
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime) {

        if (startTime == null) {
            startTime = LocalDateTime.now().minusHours(24);
        }
        if (endTime == null) {
            endTime = LocalDateTime.now();
        }

        return Result.success(ganttService.getGanttStats(startTime, endTime));
    }

    @GetMapping("/task-groups")
    public Result<List<String>> getTaskGroups() {
        return Result.success(ganttService.getTaskGroups());
    }
}
