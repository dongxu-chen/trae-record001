package com.meeting.booking.dto;

import lombok.Data;
import java.util.List;

@Data
public class RoomUsageStatsDTO {
    private Long roomId;
    private String roomName;
    private Long totalMinutes;
    private Double usageRate;
    private List<DailyUsageDTO> dailyUsage;
    private List<FreeSlotDTO> freeSlots;
}
