package com.meeting.booking.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class BookingCalendarDTO {
    private Long bookingId;
    private String title;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer status;
    private String userName;
}
