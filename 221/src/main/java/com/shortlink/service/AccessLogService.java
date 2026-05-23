package com.shortlink.service;

import com.shortlink.dto.HourlyStatsResponse;
import com.shortlink.dto.IpLocationResult;
import com.shortlink.dto.StatsResponse;
import com.shortlink.entity.AccessLog;
import com.shortlink.repository.AccessLogRepository;
import com.shortlink.util.UserAgentParser;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class AccessLogService {

    private final AccessLogRepository accessLogRepository;
    private final UserAgentParser userAgentParser;
    private final IpLocationService ipLocationService;

    private static final DateTimeFormatter HOUR_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:00:00");
    private static final DateTimeFormatter EXPORT_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Async
    public void logAccess(String shortCode, HttpServletRequest request) {
        try {
            AccessLog accessLog = new AccessLog();
            accessLog.setShortCode(shortCode);

            String ip = getClientIp(request);
            accessLog.setIp(ip);

            String userAgent = request.getHeader("User-Agent");
            accessLog.setUserAgent(userAgent);

            Map<String, String> uaInfo = userAgentParser.parse(userAgent);
            accessLog.setDeviceType(uaInfo.get("deviceType"));
            accessLog.setBrowser(uaInfo.get("browser"));
            accessLog.setOs(uaInfo.get("os"));

            IpLocationResult location = ipLocationService.getLocation(ip);
            accessLog.setCountry(location.getCountry());
            accessLog.setProvince(location.getProvince());
            accessLog.setCity(location.getCity());

            String referer = request.getHeader("Referer");
            accessLog.setReferer(referer);

            accessLogRepository.save(accessLog);
        } catch (Exception e) {
            log.error("记录访问日志失败", e);
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_CLIENT_IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_X_FORWARDED_FOR");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }

        if (ip != null && ip.contains(",")) {
            ip = ip.split(",")[0].trim();
        }

        return ip;
    }

    public StatsResponse getStats(String shortCode, int days) {
        LocalDateTime endTime = LocalDateTime.now();
        LocalDateTime startTime = endTime.minusDays(days);

        StatsResponse response = new StatsResponse();
        response.setShortCode(shortCode);

        Long totalPv = accessLogRepository.countByDate(shortCode, startTime, endTime)
                .stream()
                .mapToLong(arr -> ((Number) arr[1]).longValue())
                .sum();
        response.setTotalPv(totalPv);

        Long totalUv = accessLogRepository.countDistinctIpByShortCodeAndAccessTimeBetween(
                shortCode, startTime, endTime);
        response.setTotalUv(totalUv != null ? totalUv : 0L);

        Map<String, Long> deviceStats = new HashMap<>();
        List<Object[]> deviceData = accessLogRepository.countByDeviceType(shortCode);
        for (Object[] row : deviceData) {
            String device = (String) row[0];
            Long count = ((Number) row[1]).longValue();
            deviceStats.put(device, count);
        }
        response.setDeviceStats(deviceStats);

        Map<String, Long> browserStats = new HashMap<>();
        List<Object[]> browserData = accessLogRepository.countByBrowser(shortCode);
        for (Object[] row : browserData) {
            String browser = (String) row[0];
            Long count = ((Number) row[1]).longValue();
            browserStats.put(browser, count);
        }
        response.setBrowserStats(browserStats);

        Map<String, Long> regionStats = new HashMap<>();
        List<Object[]> regionData = accessLogRepository.countByProvince(shortCode);
        for (Object[] row : regionData) {
            String region = (String) row[0];
            Long count = ((Number) row[1]).longValue();
            regionStats.put(region, count);
        }
        response.setRegionStats(regionStats);

        Map<LocalDate, Long> dailyStats = new HashMap<>();
        List<Object[]> dailyData = accessLogRepository.countByDate(shortCode, startTime, endTime);
        for (Object[] row : dailyData) {
            LocalDate date = (LocalDate) row[0];
            Long count = ((Number) row[1]).longValue();
            dailyStats.put(date, count);
        }
        response.setDailyStats(dailyStats);

        return response;
    }

    public HourlyStatsResponse getHourlyStats(String shortCode, int days) {
        LocalDateTime endTime = LocalDateTime.now();
        LocalDateTime startTime = endTime.minusDays(days);

        HourlyStatsResponse response = new HourlyStatsResponse();
        response.setShortCode(shortCode);

        List<Object[]> hourlyData = accessLogRepository.countByHour(shortCode, startTime, endTime);
        Map<String, Long> hourMap = new HashMap<>();
        for (Object[] row : hourlyData) {
            String hourStr = (String) row[0];
            Long count = ((Number) row[1]).longValue();
            hourMap.put(hourStr, count);
        }

        List<HourlyStatsResponse.HourlyData> hourlyList = new ArrayList<>();
        LocalDateTime currentHour = startTime.withMinute(0).withSecond(0).withNano(0);
        long totalPv = 0;

        while (!currentHour.isAfter(endTime)) {
            String hourKey = currentHour.format(HOUR_FORMATTER);
            Long count = hourMap.getOrDefault(hourKey, 0L);
            hourlyList.add(new HourlyStatsResponse.HourlyData(currentHour, count));
            totalPv += count;
            currentHour = currentHour.plusHours(1);
        }

        response.setHourlyData(hourlyList);
        response.setTotalPv(totalPv);

        Long totalUv = accessLogRepository.countDistinctIpByShortCodeAndAccessTimeBetween(
                shortCode, startTime, endTime);
        response.setTotalUv(totalUv != null ? totalUv : 0L);

        return response;
    }

    public byte[] exportStatsCsv(String shortCode, int days) {
        LocalDateTime endTime = LocalDateTime.now();
        LocalDateTime startTime = endTime.minusDays(days);

        List<AccessLog> logs = accessLogRepository.findByShortCodeAndAccessTimeBetween(
                shortCode, startTime, endTime);

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (PrintWriter writer = new PrintWriter(
                new OutputStreamWriter(baos, StandardCharsets.UTF_8))) {

            writer.write('\ufeff');
            writer.println("访问时间,IP地址,设备类型,浏览器,操作系统,国家,省份,城市,来源页面");

            for (AccessLog log : logs) {
                writer.print(escapeCsv(log.getAccessTime() != null ? log.getAccessTime().format(EXPORT_FORMATTER) : ""));
                writer.print(",");
                writer.print(escapeCsv(log.getIp()));
                writer.print(",");
                writer.print(escapeCsv(log.getDeviceType()));
                writer.print(",");
                writer.print(escapeCsv(log.getBrowser()));
                writer.print(",");
                writer.print(escapeCsv(log.getOs()));
                writer.print(",");
                writer.print(escapeCsv(log.getCountry()));
                writer.print(",");
                writer.print(escapeCsv(log.getProvince()));
                writer.print(",");
                writer.print(escapeCsv(log.getCity()));
                writer.print(",");
                writer.println(escapeCsv(log.getReferer()));
            }

            writer.flush();
        } catch (Exception e) {
            log.error("导出CSV失败", e);
        }

        return baos.toByteArray();
    }

    private String escapeCsv(String field) {
        if (field == null) {
            return "";
        }
        if (field.contains(",") || field.contains("\"") || field.contains("\n")) {
            return "\"" + field.replace("\"", "\"\"") + "\"";
        }
        return field;
    }
}
