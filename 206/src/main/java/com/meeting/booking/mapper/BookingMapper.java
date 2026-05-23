package com.meeting.booking.mapper;

import com.meeting.booking.dto.BookingQueryDTO;
import com.meeting.booking.entity.Booking;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface BookingMapper {

    Booking selectById(@Param("id") Long id);

    List<Booking> selectList(BookingQueryDTO query);

    List<Booking> selectConflictBookings(
            @Param("roomId") Long roomId,
            @Param("startTime") LocalDateTime startTime,
            @Param("endTime") LocalDateTime endTime,
            @Param("excludeBookingId") Long excludeBookingId
    );

    List<Booking> selectByUserId(@Param("userId") Long userId);

    List<Booking> selectByRecurringParentId(@Param("recurringParentId") Long recurringParentId);

    int insert(Booking booking);

    int update(Booking booking);

    int updateStatus(
            @Param("id") Long id,
            @Param("status") Integer status,
            @Param("version") Integer version
    );

    int deleteById(@Param("id") Long id);

    int batchInsert(@Param("list") List<Booking> bookings);

    int countByUserId(@Param("userId") Long userId);

    long countList(BookingQueryDTO query);
}
