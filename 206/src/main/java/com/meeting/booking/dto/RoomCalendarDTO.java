package com.meeting.booking.dto;

import lombok.Data;
import java.util.List;

@Data
public class RoomCalendarDTO {
    private Long roomId;
    private String roomName;
    private List<BookingCalendarDTO> bookings;
}
