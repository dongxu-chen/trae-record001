package com.meeting.booking.dto;

import lombok.Data;
import java.time.LocalDate;

@Data
public class StatisticsQueryDTO {
    private Long roomId;
    private LocalDate startDate;
    private LocalDate endDate;
    private String period;
}
