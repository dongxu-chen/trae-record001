package com.grayrelease.release.service;

import com.grayrelease.common.enums.ReleaseWindowStatus;
import com.grayrelease.common.model.ReleaseCalendar;
import com.grayrelease.common.util.IdGenerator;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class ReleaseCalendarManager {

    private final Map<String, ReleaseCalendar> calendarStore = new ConcurrentHashMap<>();

    private final Map<String, List<ReleaseCalendar.LockPeriod>> lockPeriodsStore = new ConcurrentHashMap<>();

    public ReleaseCalendar createCalendar(ReleaseCalendar calendar) {
        String calendarId = IdGenerator.generateId();
        calendar.setId(calendarId);
        calendar.setCreatedAt(LocalDateTime.now());
        calendar.setUpdatedAt(LocalDateTime.now());

        if (calendar.getStatus() == null) {
            calendar.setStatus(ReleaseWindowStatus.OPEN);
        }

        calendarStore.put(calendarId, calendar);

        String serviceKey = getServiceKey(calendar.getServiceName());
        lockPeriodsStore.computeIfAbsent(serviceKey, k -> new ArrayList<>());

        log.info("Release calendar created: id={}, service={}, name={}",
                calendarId, calendar.getServiceName(), calendar.getName());
        return calendar;
    }

    public ReleaseCalendar.LockPeriod createLockPeriod(String serviceName, ReleaseCalendar.LockPeriod lockPeriod) {
        String lockId = IdGenerator.generateId();
        lockPeriod.setId(lockId);

        String serviceKey = getServiceKey(serviceName);
        lockPeriodsStore.computeIfAbsent(serviceKey, k -> new ArrayList<>()).add(lockPeriod);

        log.info("Lock period created: id={}, service={}, name={}, from={}, to={}",
                lockId, serviceName, lockPeriod.getName(),
                lockPeriod.getStartTime(), lockPeriod.getEndTime());
        return lockPeriod;
    }

    public ReleaseWindowStatus checkReleaseWindow(String serviceName, LocalDateTime time) {
        if (isInLockPeriod(serviceName, time)) {
            return ReleaseWindowStatus.LOCKED;
        }

        List<ReleaseCalendar> calendars = getCalendarsByService(serviceName);
        if (calendars.isEmpty()) {
            return ReleaseWindowStatus.OPEN;
        }

        for (ReleaseCalendar calendar : calendars) {
            if (isTimeInCalendar(calendar, time)) {
                if (calendar.getStatus() == ReleaseWindowStatus.LOCKED) {
                    return ReleaseWindowStatus.LOCKED;
                }
                return calendar.getStatus();
            }
        }

        return ReleaseWindowStatus.CLOSED;
    }

    public boolean canRelease(String serviceName, LocalDateTime time) {
        ReleaseWindowStatus status = checkReleaseWindow(serviceName, time);
        return status == ReleaseWindowStatus.OPEN;
    }

    public ReleaseWindowStatus getCurrentStatus(String serviceName) {
        return checkReleaseWindow(serviceName, LocalDateTime.now());
    }

    public List<ReleaseCalendar> getUpcomingWindows(String serviceName, int days) {
        LocalDateTime start = LocalDateTime.now();
        LocalDateTime end = start.plusDays(days);

        List<ReleaseCalendar> result = new ArrayList<>();
        List<ReleaseCalendar> calendars = getCalendarsByService(serviceName);

        for (ReleaseCalendar calendar : calendars) {
            LocalDateTime calStart = calendar.getStartDate() != null ?
                    calendar.getStartDate().atStartOfDay() : null;
            LocalDateTime calEnd = calendar.getEndDate() != null ?
                    calendar.getEndDate().atTime(LocalTime.MAX) : null;

            if (calStart != null && calEnd != null) {
                if (!(calEnd.isBefore(start) || calStart.isAfter(end))) {
                    result.add(calendar);
                }
            }
        }

        return result;
    }

    public List<ReleaseCalendar.LockPeriod> getActiveLockPeriods(String serviceName) {
        LocalDateTime now = LocalDateTime.now();
        String serviceKey = getServiceKey(serviceName);
        List<ReleaseCalendar.LockPeriod> periods = lockPeriodsStore.getOrDefault(serviceKey, new ArrayList<>());

        return periods.stream()
                .filter(p -> !now.isBefore(p.getStartTime()) && !now.isAfter(p.getEndTime()))
                .collect(Collectors.toList());
    }

    public List<ReleaseCalendar.LockPeriod> getUpcomingLockPeriods(String serviceName, int days) {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime end = now.plusDays(days);
        String serviceKey = getServiceKey(serviceName);
        List<ReleaseCalendar.LockPeriod> periods = lockPeriodsStore.getOrDefault(serviceKey, new ArrayList<>());

        return periods.stream()
                .filter(p -> !p.getEndTime().isBefore(now) && !p.getStartTime().isAfter(end))
                .collect(Collectors.toList());
    }

    public boolean isInLockPeriod(String serviceName, LocalDateTime time) {
        String serviceKey = getServiceKey(serviceName);
        List<ReleaseCalendar.LockPeriod> periods = lockPeriodsStore.getOrDefault(serviceKey, new ArrayList<>());

        for (ReleaseCalendar.LockPeriod period : periods) {
            if (!time.isBefore(period.getStartTime()) && !time.isAfter(period.getEndTime())) {
                return true;
            }
        }
        return false;
    }

    private boolean isTimeInCalendar(ReleaseCalendar calendar, LocalDateTime time) {
        LocalDate date = time.toLocalDate();
        LocalTime timeOfDay = time.toLocalTime();

        if (calendar.getStartDate() != null && date.isBefore(calendar.getStartDate())) {
            return false;
        }
        if (calendar.getEndDate() != null && date.isAfter(calendar.getEndDate())) {
            return false;
        }

        if (calendar.getExcludedDates() != null && calendar.getExcludedDates().contains(date)) {
            return false;
        }

        if (calendar.getAllowedDays() != null && !calendar.getAllowedDays().isEmpty()) {
            DayOfWeek dayOfWeek = date.getDayOfWeek();
            if (!calendar.getAllowedDays().contains(dayOfWeek)) {
                return false;
            }
        }

        if (calendar.getStartTime() != null && calendar.getEndTime() != null) {
            if (timeOfDay.isBefore(calendar.getStartTime()) || timeOfDay.isAfter(calendar.getEndTime())) {
                return false;
            }
        }

        return true;
    }

    public List<ReleaseCalendar> getCalendarsByService(String serviceName) {
        return calendarStore.values().stream()
                .filter(c -> serviceName.equals(c.getServiceName()))
                .collect(Collectors.toList());
    }

    public ReleaseCalendar getCalendar(String calendarId) {
        return calendarStore.get(calendarId);
    }

    public boolean removeLockPeriod(String serviceName, String lockId) {
        String serviceKey = getServiceKey(serviceName);
        List<ReleaseCalendar.LockPeriod> periods = lockPeriodsStore.get(serviceKey);
        if (periods != null) {
            return periods.removeIf(p -> lockId.equals(p.getId()));
        }
        return false;
    }

    public boolean deleteCalendar(String calendarId) {
        return calendarStore.remove(calendarId) != null;
    }

    public void clearServiceCalendar(String serviceName) {
        List<String> toRemove = calendarStore.entrySet().stream()
                .filter(e -> serviceName.equals(e.getValue().getServiceName()))
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
        toRemove.forEach(calendarStore::remove);

        lockPeriodsStore.remove(getServiceKey(serviceName));
        log.info("Release calendar cleared for service: {}", serviceName);
    }

    private String getServiceKey(String serviceName) {
        return serviceName;
    }
}