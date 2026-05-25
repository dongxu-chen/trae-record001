package com.ticket.calendar;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Slf4j
@Service
@RequiredArgsConstructor
public class WorkCalendarService {

    private final WorkCalendarConfig calendarConfig;

    private final List<LocalDate> holidays = new CopyOnWriteArrayList<>();
    private final List<LocalDate> workdays = new CopyOnWriteArrayList<>();

    public LocalDateTime calculateDeadline(LocalDateTime startTime, int workMinutes) {
        if (workMinutes <= 0) {
            return startTime;
        }

        log.debug("计算截止时间: 开始时间={}, 工作分钟={}", startTime, workMinutes);

        LocalDateTime current = adjustToWorkTime(startTime);
        int remainingMinutes = workMinutes;

        while (remainingMinutes > 0) {
            if (!isWorkday(current.toLocalDate())) {
                current = nextWorkdayStart(current);
                continue;
            }

            LocalTime workStart = calendarConfig.getWorkStartTime();
            LocalTime workEnd = calendarConfig.getWorkEndTime();
            LocalTime noonStart = calendarConfig.getNoonStartTime();
            LocalTime noonEnd = calendarConfig.getNoonEndTime();

            LocalTime currentTime = current.toLocalTime();

            if (currentTime.isBefore(workStart)) {
                current = current.with(workStart);
                continue;
            }

            if (currentTime.isAfter(workEnd)) {
                current = nextWorkdayStart(current);
                continue;
            }

            if (currentTime.isAfter(noonStart) && currentTime.isBefore(noonEnd)) {
                current = current.with(noonEnd);
                continue;
            }

            LocalTime periodEnd;
            if (currentTime.isBefore(noonStart)) {
                periodEnd = noonStart;
            } else if (currentTime.isAfter(noonEnd)) {
                periodEnd = workEnd;
            } else {
                current = current.with(noonEnd);
                continue;
            }

            int minutesInPeriod = (int) java.time.Duration.between(currentTime, periodEnd).toMinutes();

            if (remainingMinutes <= minutesInPeriod) {
                current = current.plusMinutes(remainingMinutes);
                remainingMinutes = 0;
            } else {
                remainingMinutes -= minutesInPeriod;
                current = nextWorkdayStart(current);
            }
        }

        log.debug("计算完成: 截止时间={}", current);
        return current;
    }

    private LocalDateTime adjustToWorkTime(LocalDateTime time) {
        LocalDate date = time.toLocalDate();
        LocalTime localTime = time.toLocalTime();

        if (!isWorkday(date)) {
            return nextWorkdayStart(time);
        }

        LocalTime workStart = calendarConfig.getWorkStartTime();
        LocalTime workEnd = calendarConfig.getWorkEndTime();

        if (localTime.isBefore(workStart)) {
            return LocalDateTime.of(date, workStart);
        }

        if (localTime.isAfter(workEnd)) {
            return nextWorkdayStart(time);
        }

        LocalTime noonStart = calendarConfig.getNoonStartTime();
        LocalTime noonEnd = calendarConfig.getNoonEndTime();

        if (localTime.isAfter(noonStart) && localTime.isBefore(noonEnd)) {
            return LocalDateTime.of(date, noonEnd);
        }

        return time;
    }

    private LocalDateTime nextWorkdayStart(LocalDateTime current) {
        LocalDate nextDate = current.toLocalDate().plusDays(1);
        while (!isWorkday(nextDate)) {
            nextDate = nextDate.plusDays(1);
        }
        return LocalDateTime.of(nextDate, calendarConfig.getWorkStartTime());
    }

    public boolean isWorkday(LocalDate date) {
        if (isHoliday(date)) {
            return false;
        }
        if (isExtraWorkday(date)) {
            return true;
        }
        DayOfWeek dayOfWeek = date.getDayOfWeek();
        return calendarConfig.getWorkDays().contains(dayOfWeek);
    }

    public boolean isHoliday(LocalDate date) {
        if (holidays.contains(date)) {
            return true;
        }
        return calendarConfig.getFixedHolidays().stream()
                .anyMatch(h -> h.getMonth() == date.getMonth() && h.getDayOfMonth() == date.getDayOfMonth());
    }

    public boolean isExtraWorkday(LocalDate date) {
        return workdays.contains(date);
    }

    public long calculateWorkMinutes(LocalDateTime start, LocalDateTime end) {
        if (start.isAfter(end)) {
            return -calculateWorkMinutes(end, start);
        }

        long totalMinutes = 0;
        LocalDateTime current = adjustToWorkTime(start);

        while (current.isBefore(end)) {
            if (!isWorkday(current.toLocalDate())) {
                current = nextWorkdayStart(current);
                continue;
            }

            LocalTime workStart = calendarConfig.getWorkStartTime();
            LocalTime workEnd = calendarConfig.getWorkEndTime();
            LocalTime noonStart = calendarConfig.getNoonStartTime();
            LocalTime noonEnd = calendarConfig.getNoonEndTime();

            LocalTime currentTime = current.toLocalTime();
            LocalTime periodEnd;

            if (currentTime.isBefore(workStart)) {
                current = current.with(workStart);
                continue;
            } else if (currentTime.isBefore(noonStart)) {
                periodEnd = noonStart;
            } else if (currentTime.isBefore(noonEnd)) {
                current = current.with(noonEnd);
                continue;
            } else if (currentTime.isBefore(workEnd)) {
                periodEnd = workEnd;
            } else {
                current = nextWorkdayStart(current);
                continue;
            }

            LocalDateTime periodEndDateTime = current.with(periodEnd);
            if (periodEndDateTime.isAfter(end)) {
                periodEndDateTime = end;
            }

            totalMinutes += java.time.Duration.between(current, periodEndDateTime).toMinutes();
            current = periodEndDateTime;

            if (periodEnd.equals(workEnd)) {
                current = nextWorkdayStart(current);
            }
        }

        return totalMinutes;
    }

    public boolean isWorkTime(LocalDateTime time) {
        if (!isWorkday(time.toLocalDate())) {
            return false;
        }

        LocalTime localTime = time.toLocalTime();
        LocalTime workStart = calendarConfig.getWorkStartTime();
        LocalTime workEnd = calendarConfig.getWorkEndTime();
        LocalTime noonStart = calendarConfig.getNoonStartTime();
        LocalTime noonEnd = calendarConfig.getNoonEndTime();

        if (localTime.isBefore(workStart) || localTime.isAfter(workEnd)) {
            return false;
        }

        return !(localTime.isAfter(noonStart) && localTime.isBefore(noonEnd));
    }

    public void addHoliday(LocalDate date) {
        if (!holidays.contains(date)) {
            holidays.add(date);
            workdays.remove(date);
            log.info("添加节假日: {}", date);
        }
    }

    public void addHolidays(List<LocalDate> dates) {
        dates.forEach(this::addHoliday);
    }

    public void addWorkday(LocalDate date) {
        if (!workdays.contains(date)) {
            workdays.add(date);
            holidays.remove(date);
            log.info("添加调休工作日: {}", date);
        }
    }

    public void addWorkdays(List<LocalDate> dates) {
        dates.forEach(this::addWorkday);
    }

    public void removeHoliday(LocalDate date) {
        holidays.remove(date);
        log.info("移除节假日: {}", date);
    }

    public void removeWorkday(LocalDate date) {
        workdays.remove(date);
        log.info("移除调休工作日: {}", date);
    }

    public List<LocalDate> getHolidaysForYear(int year) {
        List<LocalDate> result = new ArrayList<>();
        for (LocalDate holiday : holidays) {
            if (holiday.getYear() == year) {
                result.add(holiday);
            }
        }
        return result;
    }

    public List<LocalDate> getWorkdaysForYear(int year) {
        List<LocalDate> result = new ArrayList<>();
        for (LocalDate workday : workdays) {
            if (workday.getYear() == year) {
                result.add(workday);
            }
        }
        return result;
    }
}
