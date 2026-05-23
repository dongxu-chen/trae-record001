package com.meeting.booking.service;

import com.meeting.booking.dto.*;
import com.meeting.booking.entity.Booking;
import com.meeting.booking.entity.MeetingRoom;
import com.meeting.booking.entity.User;
import com.meeting.booking.mapper.BookingMapper;
import com.meeting.booking.mapper.MeetingRoomMapper;
import com.meeting.booking.mapper.UserMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.*;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class CalendarService {

    @Autowired
    private BookingMapper bookingMapper;

    @Autowired
    private MeetingRoomMapper meetingRoomMapper;

    @Autowired
    private UserMapper userMapper;

    public CalendarViewDTO getCalendarView(int year, int month, Long roomId) {
        CalendarViewDTO calendarView = new CalendarViewDTO();
        LocalDate monthDate = LocalDate.of(year, month, 1);
        calendarView.setMonth(monthDate);

        LocalDate startDate = monthDate.withDayOfMonth(1);
        LocalDate endDate = monthDate.withDayOfMonth(monthDate.lengthOfMonth());
        LocalDateTime startDateTime = startDate.atStartOfDay();
        LocalDateTime endDateTime = endDate.atTime(23, 59, 59);

        List<MeetingRoom> rooms;
        if (roomId != null) {
            MeetingRoom room = meetingRoomMapper.selectById(roomId);
            rooms = room != null ? Collections.singletonList(room) : Collections.emptyList();
        } else {
            rooms = meetingRoomMapper.selectAll();
        }

        Map<Long, RoomCalendarDTO> roomCalendarMap = new LinkedHashMap<>();

        for (MeetingRoom room : rooms) {
            RoomCalendarDTO roomCalendar = new RoomCalendarDTO();
            roomCalendar.setRoomId(room.getId());
            roomCalendar.setRoomName(room.getName());

            List<Booking> roomBookings = bookingMapper.selectByRoomId(room.getId()).stream()
                    .filter(b -> !b.getEndTime().isBefore(startDateTime) && !b.getStartTime().isAfter(endDateTime))
                    .filter(b -> b.getStatus() == 1 || b.getStatus() == 2 || b.getStatus() == 4)
                    .sorted(Comparator.comparing(Booking::getStartTime))
                    .collect(Collectors.toList());

            List<BookingCalendarDTO> bookingCalendars = new ArrayList<>();
            for (Booking booking : roomBookings) {
                BookingCalendarDTO dto = convertToCalendarDTO(booking);
                bookingCalendars.add(dto);
            }

            roomCalendar.setBookings(bookingCalendars);
            roomCalendarMap.put(room.getId(), roomCalendar);
        }

        calendarView.setRooms(roomCalendarMap);
        return calendarView;
    }

    private BookingCalendarDTO convertToCalendarDTO(Booking booking) {
        BookingCalendarDTO dto = new BookingCalendarDTO();
        dto.setBookingId(booking.getId());
        dto.setTitle(booking.getTitle());
        dto.setStartTime(booking.getStartTime());
        dto.setEndTime(booking.getEndTime());
        dto.setStatus(booking.getStatus());

        if (booking.getUserId() != null) {
            User user = userMapper.selectById(booking.getUserId());
            if (user != null) {
                dto.setUserName(user.getName());
            }
        }

        return dto;
    }
}
