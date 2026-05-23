package com.meeting.booking.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class RoomQueryDTO {
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer minCapacity;
    private Integer maxCapacity;
    private List<String> equipmentTypes;
    private Integer status;
    private String keyword;
}
