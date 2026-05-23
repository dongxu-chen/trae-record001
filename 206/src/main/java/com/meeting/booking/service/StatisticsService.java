package com.meeting.booking.service;

import com.meeting.booking.common.BookingStatusEnum;
import com.meeting.booking.dto.*;
import com.meeting.booking.entity.Booking;
import com.meeting.booking.entity.MeetingRoom;
import com.meeting.booking.mapper.BookingMapper;
import com.meeting.booking.mapper.MeetingRoomMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.*;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class StatisticsService {

    @Autowired
    private BookingMapper bookingMapper;

    @Autowired
    private MeetingRoomMapper meetingRoomMapper;

    private static final int WORK_START_HOUR = 8;
    private static final int WORK_END_HOUR = 20;
    private static final int WORK_HOURS_PER_DAY = WORK_END_HOUR - WORK_START_HOUR;

    public List<RoomUsageStatsDTO> getRoomUsageStatistics(StatisticsQueryDTO query) {
        LocalDate startDate = query.getStartDate() != null ? query.getStartDate() : LocalDate.now().minusWeeks(1);
        LocalDate endDate = query.getEndDate() != null ? query.getEndDate() : LocalDate.now();
        String period = query.getPeriod() != null ? query.getPeriod() : "DAY";

        List<MeetingRoom> rooms;
        if (query.getRoomId() != null) {
            MeetingRoom room = meetingRoomMapper.selectById(query.getRoomId());
            rooms = room != null ? Collections.singletonList(room) : Collections.emptyList();
        } else {
            rooms = meetingRoomMapper.selectAll();
        }

        List<RoomUsageStatsDTO> result = new ArrayList<>();
        for (MeetingRoom room : rooms) {
            RoomUsageStatsDTO stats = calculateRoomStats(room, startDate, endDate, period);
            result.add(stats);
        }

        return result;
    }

    private RoomUsageStatsDTO calculateRoomStats(MeetingRoom room, LocalDate startDate, LocalDate endDate, String period) {
        RoomUsageStatsDTO stats = new RoomUsageStatsDTO();
        stats.setRoomId(room.getId());
        stats.setRoomName(room.getName());

        List<Booking> bookings = getBookingsInPeriod(room.getId(), startDate, endDate);

        long totalMinutes = 0;
        Map<LocalDate, Long> dailyMinutes = new LinkedHashMap<>();
        List<LocalDate> dates = getDatesInPeriod(startDate, endDate, period);

        for (LocalDate date : dates) {
            long minutes = calculateDailyUsage(bookings, date);
            dailyMinutes.put(date, minutes);
            totalMinutes += minutes;
        }

        stats.setTotalMinutes(totalMinutes);

        long totalWorkMinutes = dates.size() * WORK_HOURS_PER_DAY * 60L;
        double usageRate = totalWorkMinutes > 0 ? (totalMinutes * 100.0 / totalWorkMinutes) : 0;
        stats.setUsageRate(Math.round(usageRate * 100.0) / 100.0);

        List<DailyUsageDTO> dailyUsage = new ArrayList<>();
        for (Map.Entry<LocalDate, Long> entry : dailyMinutes.entrySet()) {
            DailyUsageDTO daily = new DailyUsageDTO();
            daily.setDate(entry.getKey());
            daily.setUsedMinutes(entry.getValue());
            double dailyRate = (entry.getValue() * 100.0) / (WORK_HOURS_PER_DAY * 60);
            daily.setUsageRate(Math.round(dailyRate * 100.0) / 100.0);
            daily.setBookingCount(countBookingsOnDate(bookings, entry.getKey()));
            dailyUsage.add(daily);
        }
        stats.setDailyUsage(dailyUsage);

        stats.setFreeSlots(calculateFreeSlots(room.getId(), bookings, startDate, endDate));

        return stats;
    }

    private List<Booking> getBookingsInPeriod(Long roomId, LocalDate startDate, LocalDate endDate) {
        LocalDateTime startDateTime = startDate.atStartOfDay();
        LocalDateTime endDateTime = endDate.atTime(23, 59, 59);

        List<Booking> allBookings = bookingMapper.selectByRoomId(roomId);
        return allBookings.stream()
                .filter(b -> b.getStatus() == BookingStatusEnum.CONFIRMED.getCode() ||
                        b.getStatus() == BookingStatusEnum.COMPLETED.getCode())
                .filter(b -> !b.getEndTime().isBefore(startDateTime) && !b.getStartTime().isAfter(endDateTime))
                .sorted(Comparator.comparing(Booking::getStartTime))
                .collect(Collectors.toList());
    }

    private List<LocalDate> getDatesInPeriod(LocalDate startDate, LocalDate endDate, String period) {
        List<LocalDate> dates = new ArrayList<>();
        LocalDate current = startDate;

        switch (period) {
            case "WEEK":
                current = startDate.with(DayOfWeek.MONDAY);
                while (!current.isAfter(endDate)) {
                    dates.add(current);
                    current = current.plusWeeks(1);
                }
                break;
            case "MONTH":
                current = startDate.withDayOfMonth(1);
                while (!current.isAfter(endDate)) {
                    dates.add(current);
                    current = current.plusMonths(1).withDayOfMonth(1);
                }
                break;
            default:
                while (!current.isAfter(endDate)) {
                    dates.add(current);
                    current = current.plusDays(1);
                }
        }

        return dates;
    }

    private long calculateDailyUsage(List<Booking> bookings, LocalDate date) {
        long totalMinutes = 0;
        LocalDateTime dayStart = date.atTime(WORK_START_HOUR, 0);
        LocalDateTime dayEnd = date.atTime(WORK_END_HOUR, 0);

        for (Booking booking : bookings) {
            LocalDateTime bookingStart = booking.getStartTime();
            LocalDateTime bookingEnd = booking.getEndTime();

            if (bookingEnd.isBefore(dayStart) || bookingStart.isAfter(dayEnd)) {
                continue;
            }

            LocalDateTime overlapStart = bookingStart.isAfter(dayStart) ? bookingStart : dayStart;
            LocalDateTime overlapEnd = bookingEnd.isBefore(dayEnd) ? bookingEnd : dayEnd;

            totalMinutes += Duration.between(overlapStart, overlapEnd).toMinutes();
        }

        return totalMinutes;
    }

    private int countBookingsOnDate(List<Booking> bookings, LocalDate date) {
        return (int) bookings.stream()
                .filter(b -> b.getStartTime().toLocalDate().equals(date) ||
                        b.getEndTime().toLocalDate().equals(date))
                .count();
    }

    private List<FreeSlotDTO> calculateFreeSlots(Long roomId, List<Booking> bookings, LocalDate startDate, LocalDate endDate) {
        List<FreeSlotDTO> freeSlots = new ArrayList<>();
        LocalDate currentDate = startDate;

        while (!currentDate.isAfter(endDate)) {
            LocalDateTime workStart = currentDate.atTime(WORK_START_HOUR, 0);
            LocalDateTime workEnd = currentDate.atTime(WORK_END_HOUR, 0);

            List<Booking> dayBookings = bookings.stream()
                    .filter(b -> !b.getEndTime().isBefore(workStart) && !b.getStartTime().isAfter(workEnd))
                    .sorted(Comparator.comparing(Booking::getStartTime))
                    .collect(Collectors.toList());

            LocalDateTime currentTime = workStart;

            for (Booking booking : dayBookings) {
                LocalDateTime bookingStart = booking.getStartTime().isAfter(workStart) ? booking.getStartTime() : workStart;
                LocalDateTime bookingEnd = booking.getEndTime().isBefore(workEnd) ? booking.getEndTime() : workEnd;

                if (currentTime.isBefore(bookingStart)) {
                    FreeSlotDTO slot = new FreeSlotDTO();
                    slot.setStartTime(currentTime);
                    slot.setEndTime(bookingStart);
                    slot.setDurationMinutes(Duration.between(currentTime, bookingStart).toMinutes());
                    freeSlots.add(slot);
                }

                currentTime = bookingEnd.isAfter(currentTime) ? bookingEnd : currentTime;
            }

            if (currentTime.isBefore(workEnd)) {
                FreeSlotDTO slot = new FreeSlotDTO();
                slot.setStartTime(currentTime);
                slot.setEndTime(workEnd);
                slot.setDurationMinutes(Duration.between(currentTime, workEnd).toMinutes());
                freeSlots.add(slot);
            }

            currentDate = currentDate.plusDays(1);
        }

        return freeSlots.stream()
                .filter(s -> s.getDurationMinutes() >= 15)
                .collect(Collectors.toList());
    }
}
