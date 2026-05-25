package com.survey.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class RespondentProfile {
    private String surveyId;
    private String surveyTitle;
    private Integer totalVisits;
    private Integer totalResponses;
    private Double completionRate;
    private TimeDistribution timeDistribution;
    private DeviceDistribution deviceDistribution;
    private DurationStats durationStats;
    private List<String> keyInsights;
}

@Data
class TimeDistribution {
    private Map<String, Integer> byHour;
    private Map<String, Integer> byWeekday;
    private String peakHour;
    private String peakDay;
}

@Data
class DeviceDistribution {
    private Map<String, Integer> byDeviceType;
    private Map<String, Integer> byOS;
    private Map<String, Integer> byBrowser;
}

@Data
class DurationStats {
    private Double averageDuration;
    private Integer minDuration;
    private Integer maxDuration;
    private Double medianDuration;
}
