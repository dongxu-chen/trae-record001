package com.checkin.dto;

import lombok.Data;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Data
public class CheckinCalendarVO {
    private String periodType;
    private String period;
    private Integer continuousDays;
    private Integer totalDays;
    private List<LocalDate> checkinDates;
    private List<LocalDate> recheckDates;
    private Map<String, Object> todayReward;
    private List<Map<String, Object>> rewards;
    private List<Map<String, Object>> treasures;
    private Integer recheckCards;
    private Integer remainingRecheckCount;
    private Boolean todayChecked;
}
