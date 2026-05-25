package com.ticket.calendar;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Configuration
@ConfigurationProperties(prefix = "ticket.calendar")
public class WorkCalendarConfig {

    private LocalTime workStartTime = LocalTime.of(9, 0);

    private LocalTime workEndTime = LocalTime.of(18, 0);

    private LocalTime noonStartTime = LocalTime.of(12, 0);

    private LocalTime noonEndTime = LocalTime.of(13, 30);

    private List<DayOfWeek> workDays = List.of(
            DayOfWeek.MONDAY,
            DayOfWeek.TUESDAY,
            DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY,
            DayOfWeek.FRIDAY
    );

    private List<LocalDate> fixedHolidays = new ArrayList<>();

    private boolean enabled = true;

    public WorkCalendarConfig() {
        initFixedHolidays();
    }

    private void initFixedHolidays() {
        fixedHolidays.add(LocalDate.of(2000, 1, 1));
        fixedHolidays.add(LocalDate.of(2000, 1, 2));
        fixedHolidays.add(LocalDate.of(2000, 1, 3));
        fixedHolidays.add(LocalDate.of(2000, 5, 1));
        fixedHolidays.add(LocalDate.of(2000, 5, 2));
        fixedHolidays.add(LocalDate.of(2000, 5, 3));
        fixedHolidays.add(LocalDate.of(2000, 10, 1));
        fixedHolidays.add(LocalDate.of(2000, 10, 2));
        fixedHolidays.add(LocalDate.of(2000, 10, 3));
        fixedHolidays.add(LocalDate.of(2000, 10, 4));
        fixedHolidays.add(LocalDate.of(2000, 10, 5));
        fixedHolidays.add(LocalDate.of(2000, 10, 6));
        fixedHolidays.add(LocalDate.of(2000, 10, 7));
    }
}
