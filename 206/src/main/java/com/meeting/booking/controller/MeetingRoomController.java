package com.meeting.booking.controller;

import com.meeting.booking.common.Result;
import com.meeting.booking.dto.RoomQueryDTO;
import com.meeting.booking.entity.MeetingRoom;
import com.meeting.booking.service.MeetingRoomService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

@RestController
@RequestMapping("/api/rooms")
public class MeetingRoomController {

    @Autowired
    private MeetingRoomService meetingRoomService;

    @GetMapping("/{id}")
    public Result<MeetingRoom> getById(@PathVariable Long id) {
        return Result.success(meetingRoomService.getById(id));
    }

    @GetMapping
    public Result<List<MeetingRoom>> list(RoomQueryDTO query) {
        return Result.success(meetingRoomService.list(query));
    }

    @GetMapping("/available")
    public Result<List<MeetingRoom>> getAvailableRooms(
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime startTime,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss") LocalDateTime endTime,
            @RequestParam(required = false) Integer minCapacity,
            @RequestParam(required = false) List<String> equipmentTypes) {
        return Result.success(meetingRoomService.getAvailableRooms(startTime, endTime, minCapacity, equipmentTypes));
    }

    @PostMapping
    public Result<Boolean> create(@RequestBody MeetingRoom room) {
        return Result.success(meetingRoomService.create(room));
    }

    @PutMapping
    public Result<Boolean> update(@RequestBody MeetingRoom room) {
        return Result.success(meetingRoomService.update(room));
    }

    @DeleteMapping("/{id}")
    public Result<Boolean> delete(@PathVariable Long id) {
        return Result.success(meetingRoomService.delete(id));
    }
}
