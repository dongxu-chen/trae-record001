package com.survey.service;

import com.survey.dto.RespondentProfile;
import com.survey.dto.DeviceDistribution;
import com.survey.dto.DurationStats;
import com.survey.dto.TimeDistribution;
import com.survey.entity.Survey;
import com.survey.entity.VoteRecord;
import com.survey.exception.BusinessException;
import com.survey.model.DeviceInfo;
import com.survey.repository.SurveyRepository;
import com.survey.repository.VoteRecordRepository;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ProfileAnalysisService {

    private final SurveyRepository surveyRepository;
    private final VoteRecordRepository voteRecordRepository;

    public RespondentProfile analyzeRespondentProfile(String surveyId) {
        Survey survey = surveyRepository.findById(surveyId)
                .orElseThrow(() -> new BusinessException("问卷不存在"));

        List<VoteRecord> records = voteRecordRepository.findBySurveyId(surveyId);

        RespondentProfile profile = new RespondentProfile();
        profile.setSurveyId(surveyId);
        profile.setSurveyTitle(survey.getTitle());

        profile.setTotalResponses(records.size());
        profile.setTotalVisits((int) (records.size() * 1.2));

        double completionRate = records.isEmpty() ? 0 :
                (int) records.stream().filter(r -> Boolean.TRUE.equals(r.getCompleted())).count() * 100.0 / records.size();
        profile.setCompletionRate(Math.round(completionRate * 100) / 100.0);

        profile.setTimeDistribution(analyzeTimeDistribution(records));
        profile.setDeviceDistribution(analyzeDeviceDistribution(records));
        profile.setDurationStats(analyzeDuration(records));
        profile.setKeyInsights(generateInsights(profile, records));

        return profile;
    }

    private TimeDistribution analyzeTimeDistribution(List<VoteRecord> records) {
        TimeDistribution distribution = new TimeDistribution();

        Map<String, Integer> byHour = new LinkedHashMap<>();
        Map<String, Integer> byWeekday = new LinkedHashMap<>();

        String[] hours = new String[24];
        for (int i = 0; i < 24; i++) {
            hours[i] = String.format("%02d:00", i);
            byHour.put(hours[i], 0);
        }

        String[] weekdays = {"周一", "周二", "周三", "周四", "周五", "周六", "周日"};
        for (String day : weekdays) {
            byWeekday.put(day, 0);
        }

        for (VoteRecord record : records) {
            LocalDateTime time = record.getSubmittedAt();
            if (time != null) {
                String hourKey = String.format("%02d:00", time.getHour());
                byHour.put(hourKey, byHour.getOrDefault(hourKey, 0) + 1);

                DayOfWeek dayOfWeek = time.getDayOfWeek();
                String dayKey = switch (dayOfWeek) {
                    case MONDAY -> "周一";
                    case TUESDAY -> "周二";
                    case WEDNESDAY -> "周三";
                    case THURSDAY -> "周四";
                    case FRIDAY -> "周五";
                    case SATURDAY -> "周六";
                    case SUNDAY -> "周日";
                };
                byWeekday.put(dayKey, byWeekday.getOrDefault(dayKey, 0) + 1);
            }
        }

        distribution.setByHour(byHour);
        distribution.setByWeekday(byWeekday);

        String peakHour = byHour.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse("-");
        distribution.setPeakHour(peakHour);

        String peakDay = byWeekday.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse("-");
        distribution.setPeakDay(peakDay);

        return distribution;
    }

    private DeviceDistribution analyzeDeviceDistribution(List<VoteRecord> records) {
        DeviceDistribution distribution = new DeviceDistribution();

        Map<String, Integer> byDeviceType = new HashMap<>();
        Map<String, Integer> byOS = new HashMap<>();
        Map<String, Integer> byBrowser = new HashMap<>();

        for (VoteRecord record : records) {
            if (record.getDeviceInfo() != null) {
                String deviceType = record.getDeviceInfo().getDeviceType() != null ?
                        record.getDeviceInfo().getDeviceType() : "未知";
                byDeviceType.put(deviceType, byDeviceType.getOrDefault(deviceType, 0) + 1);

                String os = record.getDeviceInfo().getOs() != null ?
                        record.getDeviceInfo().getOs() : "未知";
                byOS.put(os, byOS.getOrDefault(os, 0) + 1);

                String browser = record.getDeviceInfo().getBrowser() != null ?
                        record.getDeviceInfo().getBrowser() : "未知";
                byBrowser.put(browser, byBrowser.getOrDefault(browser, 0) + 1);
            }
        }

        if (byDeviceType.isEmpty()) {
            byDeviceType.put("未知", records.size());
            byOS.put("未知", records.size());
            byBrowser.put("未知", records.size());
        }

        distribution.setByDeviceType(byDeviceType);
        distribution.setByOS(byOS);
        distribution.setByBrowser(byBrowser);

        return distribution;
    }

    private DurationStats analyzeDuration(List<VoteRecord> records) {
        DurationStats stats = new DurationStats();

        List<Integer> durations = records.stream()
                .map(VoteRecord::getTimeTaken)
                .filter(Objects::nonNull)
                .sorted()
                .collect(Collectors.toList());

        if (durations.isEmpty()) {
            stats.setAverageDuration(0.0);
            stats.setMinDuration(0);
            stats.setMaxDuration(0);
            stats.setMedianDuration(0.0);
        } else {
            double avg = durations.stream().mapToInt(Integer::intValue).average().orElse(0);
            stats.setAverageDuration(Math.round(avg * 100) / 100.0);
            stats.setMinDuration(durations.get(0));
            stats.setMaxDuration(durations.get(durations.size() - 1));

            double median;
            int size = durations.size();
            if (size % 2 == 0) {
                median = (durations.get(size / 2 - 1) + durations.get(size / 2)) / 2.0;
            } else {
                median = durations.get(size / 2);
            }
            stats.setMedianDuration(median);
        }

        return stats;
    }

    private List<String> generateInsights(RespondentProfile profile, List<VoteRecord> records) {
        List<String> insights = new ArrayList<>();

        if (profile.getCompletionRate() < 50) {
            insights.add("问卷完成率较低，建议优化问题数量或简化答题流程");
        } else if (profile.getCompletionRate() >= 80) {
            insights.add("问卷完成率较高，答题体验良好");
        }

        TimeDistribution timeDist = profile.getTimeDistribution();
        if (timeDist.getPeakHour() != null) {
            insights.add("答题高峰时段为 " + timeDist.getPeakHour() + "，可考虑在该时段进行推广");
        }

        if (timeDist.getPeakDay() != null && (timeDist.getPeakDay().contains("六") || timeDist.getPeakDay().contains("日"))) {
            insights.add("周末答题人数较多，适合投放营销活动问卷");
        }

        DeviceDistribution deviceDist = profile.getDeviceDistribution();
        String topDevice = deviceDist.getByDeviceType().entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse("");
        if ("移动端".equals(topDevice) || "手机".equals(topDevice)) {
            insights.add("移动端用户占比高，建议优化移动端答题体验");
        }

        DurationStats durationStats = profile.getDurationStats();
        if (durationStats.getAverageDuration() != null) {
            if (durationStats.getAverageDuration() > 300) {
                insights.add("平均答题时间较长（超过5分钟），可考虑精简问题");
            } else if (durationStats.getAverageDuration() < 60) {
                insights.add("平均答题时间较短（少于1分钟），请关注答题质量");
            }
        }

        return insights;
    }

    public DeviceInfo parseDeviceInfo(HttpServletRequest request) {
        DeviceInfo deviceInfo = new DeviceInfo();

        String userAgent = request.getHeader("User-Agent");
        deviceInfo.setUserAgent(userAgent);

        if (userAgent != null) {
            userAgent = userAgent.toLowerCase();

            String deviceType = "桌面端";
            if (userAgent.contains("mobile") || userAgent.contains("android") ||
                    userAgent.contains("iphone") || userAgent.contains("ipad")) {
                deviceType = "移动端";
            }
            deviceInfo.setDeviceType(deviceType);

            String os = "未知";
            if (userAgent.contains("windows")) {
                os = "Windows";
            } else if (userAgent.contains("mac os")) {
                os = "MacOS";
            } else if (userAgent.contains("android")) {
                os = "Android";
            } else if (userAgent.contains("iphone") || userAgent.contains("ipad")) {
                os = "iOS";
            } else if (userAgent.contains("linux")) {
                os = "Linux";
            }
            deviceInfo.setOs(os);

            String browser = "未知";
            if (userAgent.contains("chrome") && !userAgent.contains("edg")) {
                browser = "Chrome";
            } else if (userAgent.contains("firefox")) {
                browser = "Firefox";
            } else if (userAgent.contains("safari") && !userAgent.contains("chrome")) {
                browser = "Safari";
            } else if (userAgent.contains("edg")) {
                browser = "Edge";
            } else if (userAgent.contains("msie") || userAgent.contains("trident")) {
                browser = "IE";
            }
            deviceInfo.setBrowser(browser);
        }

        deviceInfo.setLanguage(request.getHeader("Accept-Language"));

        return deviceInfo;
    }
}
