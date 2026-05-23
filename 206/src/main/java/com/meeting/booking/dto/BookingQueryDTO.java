package com.meeting.booking.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class BookingQueryDTO {
    private Long userId;
    private Long roomId;
    private Integer status;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer pageNum = 1;
    private Integer pageSize = 10;
}
