package com.meeting.booking.service;

import com.meeting.booking.dto.RoomQueryDTO;
import com.meeting.booking.entity.MeetingRoom;
import com.meeting.booking.mapper.MeetingRoomMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class MeetingRoomService {

    @Autowired
    private MeetingRoomMapper meetingRoomMapper;

    public MeetingRoom getById(Long id) {
        return meetingRoomMapper.selectById(id);
    }

    public List<MeetingRoom> list(RoomQueryDTO query) {
        return meetingRoomMapper.selectList(query);
    }

    public List<MeetingRoom> getAvailableRooms(LocalDateTime startTime, LocalDateTime endTime, 
                                               Integer minCapacity, List<String> equipmentTypes) {
        return meetingRoomMapper.selectAvailableRooms(startTime, endTime, minCapacity, equipmentTypes, null);
    }

    public boolean create(MeetingRoom room) {
        return meetingRoomMapper.insert(room) > 0;
    }

    public boolean update(MeetingRoom room) {
        return meetingRoomMapper.update(room) > 0;
    }

    public boolean delete(Long id) {
        return meetingRoomMapper.deleteById(id) > 0;
    }
}
