package com.meeting.booking.dto;

import lombok.Data;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Data
public class CalendarViewDTO {
    private LocalDate month;
    private Map<Long, RoomCalendarDTO> rooms;
}
