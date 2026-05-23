package com.meeting.booking.mapper;

import com.meeting.booking.dto.RoomQueryDTO;
import com.meeting.booking.entity.MeetingRoom;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface MeetingRoomMapper {

    MeetingRoom selectById(@Param("id") Long id);

    List<MeetingRoom> selectList(RoomQueryDTO query);

    List<MeetingRoom> selectAvailableRooms(
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            @Param("minCapacity") Integer minCapacity,
            @Param("equipmentTypes") List<String> equipmentTypes,
            @Param("excludeBookingId") Long excludeBookingId
    );

    int insert(MeetingRoom room);

    int update(MeetingRoom room);

    int deleteById(@Param("id") Long id);
}
