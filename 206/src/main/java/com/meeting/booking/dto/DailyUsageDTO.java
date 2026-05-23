package com.meeting.booking.dto;

import lombok.Data;
import java.time.LocalDate;

@Data
public class DailyUsageDTO {
    private LocalDate date;
    private Long usedMinutes;
    private Double usageRate;
    private Integer bookingCount;
}
