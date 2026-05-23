package com.meeting.booking.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class FreeSlotDTO {
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Long durationMinutes;
}
