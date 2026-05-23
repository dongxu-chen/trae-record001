package com.meeting.booking.service;

import com.meeting.booking.common.ApprovalStatusEnum;
import com.meeting.booking.common.BookingStatusEnum;
import com.meeting.booking.common.PageResult;
import com.meeting.booking.dto.BookingQueryDTO;
import com.meeting.booking.dto.BookingRequestDTO;
import com.meeting.booking.entity.Booking;
import com.meeting.booking.entity.MeetingRoom;
import com.meeting.booking.exception.BusinessException;
import com.meeting.booking.mapper.BookingMapper;
import com.meeting.booking.mapper.MeetingRoomMapper;
import com.meeting.booking.util.RedisDistributedLock;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class BookingService {

    @Autowired
    private BookingMapper bookingMapper;

    @Autowired
    private MeetingRoomMapper meetingRoomMapper;

    @Autowired
    private RedisDistributedLock redisDistributedLock;

    @Autowired
    private ApprovalService approvalService;

    @Autowired
    private NotificationService notificationService;

    private static final long LOCK_WAIT_TIME = 1;
    private static final long LOCK_LEASE_TIME = 3;

    public Booking getById(Long id) {
        return bookingMapper.selectById(id);
    }

    public PageResult<Booking> list(BookingQueryDTO query) {
        if (query.getPageNum() == null || query.getPageNum() < 1) {
            query.setPageNum(1);
        }
        if (query.getPageSize() == null || query.getPageSize() < 1 || query.getPageSize() > 100) {
            query.setPageSize(10);
        }
        List<Booking> list = bookingMapper.selectList(query);
        long total = bookingMapper.countList(query);
        return PageResult.of(list, query.getPageNum(), query.getPageSize(), total);
    }

    public List<Booking> getByUserId(Long userId) {
        return bookingMapper.selectByUserId(userId);
    }

    @Transactional(rollbackFor = Exception.class)
    public Booking createBooking(BookingRequestDTO request) {
        validateBookingRequest(request);

        MeetingRoom room = meetingRoomMapper.selectById(request.getRoomId());
        if (room == null) {
            throw new BusinessException("会议室不存在");
        }
        if (room.getStatus() != 1) {
            throw new BusinessException("会议室不可用");
        }
        if (room.getCapacity() < request.getAttendees()) {
            throw new BusinessException("会议室容量不足，最多容纳" + room.getCapacity() + "人");
        }

        if (Boolean.TRUE.equals(request.getIsRecurring())) {
            return createRecurringBookings(request, room);
        } else {
            return createSingleBooking(request, room);
        }
    }

    private void validateBookingRequest(BookingRequestDTO request) {
        if (request.getEndTime().isBefore(request.getStartTime())) {
            throw new BusinessException("结束时间不能早于开始时间");
        }
        if (request.getStartTime().isBefore(LocalDateTime.now())) {
            throw new BusinessException("不能预订过去的时间");
        }
        Duration duration = Duration.between(request.getStartTime(), request.getEndTime());
        if (duration.toMinutes() < 15) {
            throw new BusinessException("会议时长至少15分钟");
        }
        if (duration.toHours() > 8) {
            throw new BusinessException("会议时长不能超过8小时");
        }

        if (Boolean.TRUE.equals(request.getIsRecurring())) {
            if (request.getRecurringEndDate() == null) {
                throw new BusinessException("重复预订必须指定结束日期");
            }
            if (request.getRecurringEndDate().isBefore(request.getStartTime().toLocalDate())) {
                throw new BusinessException("重复结束日期不能早于开始日期");
            }
            if (request.getRecurringDays() == null || request.getRecurringDays().isEmpty()) {
                throw new BusinessException("重复预订必须指定重复日期");
            }
            long daysBetween = ChronoUnit.DAYS.between(
                    request.getStartTime().toLocalDate(),
                    request.getRecurringEndDate()
            );
            if (daysBetween > 365) {
                throw new BusinessException("重复预订周期不能超过1年");
            }
        }
    }

    private Booking createSingleBooking(BookingRequestDTO request, MeetingRoom room) {
        String lockKey = generateLockKey(request.getRoomId(), request.getStartTime(), request.getEndTime());
        String requestId = redisDistributedLock.tryLock(lockKey, LOCK_WAIT_TIME, LOCK_LEASE_TIME, TimeUnit.SECONDS);

        if (requestId == null) {
            throw new BusinessException("系统繁忙，请稍后重试");
        }

        try {
            checkConflict(request.getRoomId(), request.getStartTime(), request.getEndTime(), null);

            Booking booking = buildBooking(request, room);
            booking.setIsRecurring(0);
            applyApprovalRules(booking, request.getAttendees());
            bookingMapper.insert(booking);

            if (booking.getNeedApproval() == 1) {
                approvalService.createApprovalRecord(booking);
                notificationService.sendBookingNotification(booking, "PENDING_APPROVAL");
            } else {
                notificationService.sendBookingNotification(booking, "CREATE");
            }

            return bookingMapper.selectById(booking.getId());
        } finally {
            redisDistributedLock.unlock(lockKey, requestId);
        }
    }

    private Booking createRecurringBookings(BookingRequestDTO request, MeetingRoom room) {
        List<LocalDateTime> dateTimes = generateRecurringDateTimes(request);

        if (dateTimes.isEmpty()) {
            throw new BusinessException("没有可生成的重复预订日期");
        }

        List<String> lockKeys = new ArrayList<>();
        List<String> requestIds = new ArrayList<>();

        try {
            for (LocalDateTime startTime : dateTimes) {
                LocalDateTime endTime = startTime.plus(Duration.between(
                        request.getStartTime().toLocalTime(),
                        request.getEndTime().toLocalTime()
                ));
                String lockKey = generateLockKey(request.getRoomId(), startTime, endTime);
                String requestId = redisDistributedLock.tryLock(lockKey, LOCK_WAIT_TIME, LOCK_LEASE_TIME, TimeUnit.SECONDS);

                if (requestId == null) {
                    throw new BusinessException("系统繁忙，请稍后重试");
                }

                lockKeys.add(lockKey);
                requestIds.add(requestId);
            }

            Duration duration = Duration.between(request.getStartTime(), request.getEndTime());
            checkRecurringConflicts(request.getRoomId(), dateTimes, duration);

            List<Integer> recurringDays = request.getRecurringDays();
            String recurringDaysStr = recurringDays.stream()
                    .map(String::valueOf)
                    .collect(Collectors.joining(","));

            List<Booking> bookings = new ArrayList<>();
            Booking parentBooking = null;

            for (int i = 0; i < dateTimes.size(); i++) {
                LocalDateTime startTime = dateTimes.get(i);
                LocalDateTime endTime = startTime.plus(duration);

                Booking booking = buildBooking(request, room);
                booking.setStartTime(startTime);
                booking.setEndTime(endTime);
                booking.setIsRecurring(1);
                booking.setRecurringRule(request.getRecurringRule());
                booking.setRecurringDays(recurringDaysStr);
                booking.setRecurringEndDate(request.getRecurringEndDate());
                applyApprovalRules(booking, request.getAttendees());

                if (i == 0) {
                    bookingMapper.insert(booking);
                    parentBooking = booking;

                    if (booking.getNeedApproval() == 1) {
                        approvalService.createApprovalRecord(booking);
                        notificationService.sendBookingNotification(booking, "PENDING_APPROVAL");
                    } else {
                        notificationService.sendBookingNotification(booking, "CREATE");
                    }
                } else {
                    booking.setRecurringParentId(parentBooking.getId());
                    bookings.add(booking);
                }
            }

            if (!bookings.isEmpty()) {
                bookingMapper.batchInsert(bookings);
                for (Booking booking : bookings) {
                    if (booking.getNeedApproval() == 1) {
                        approvalService.createApprovalRecord(booking);
                    }
                }
            }

            if (parentBooking != null) {
                parentBooking.setRecurringParentId(parentBooking.getId());
                bookingMapper.update(parentBooking);
            }

            return bookingMapper.selectById(parentBooking.getId());
        } finally {
            for (int i = 0; i < lockKeys.size(); i++) {
                redisDistributedLock.unlock(lockKeys.get(i), requestIds.get(i));
            }
        }
    }

    private void applyApprovalRules(Booking booking, int attendees) {
        if (approvalService.needsApproval(attendees)) {
            booking.setNeedApproval(1);
            booking.setApprovalStatus(ApprovalStatusEnum.PENDING.getCode());
            booking.setStatus(BookingStatusEnum.PENDING_APPROVAL.getCode());
        } else {
            booking.setNeedApproval(0);
            booking.setApprovalStatus(null);
            booking.setStatus(BookingStatusEnum.PENDING.getCode());
        }
    }

    private List<LocalDateTime> generateRecurringDateTimes(BookingRequestDTO request) {
        List<LocalDateTime> result = new ArrayList<>();
        LocalDate startDate = request.getStartTime().toLocalDate();
        LocalDate endDate = request.getRecurringEndDate();
        List<Integer> recurringDays = request.getRecurringDays();
        LocalTime startTime = request.getStartTime().toLocalTime();

        LocalDate currentDate = startDate;

        while (!currentDate.isAfter(endDate)) {
            DayOfWeek dayOfWeek = currentDate.getDayOfWeek();
            int dayValue = dayOfWeek.getValue();

            if (recurringDays.contains(dayValue)) {
                LocalDateTime dateTime = LocalDateTime.of(currentDate, startTime);
                if (!dateTime.isBefore(LocalDateTime.now())) {
                    result.add(dateTime);
                }
            }

            if ("WEEKLY".equals(request.getRecurringRule())) {
                currentDate = currentDate.plusWeeks(1);
            } else if ("DAILY".equals(request.getRecurringRule())) {
                currentDate = currentDate.plusDays(1);
            } else {
                currentDate = currentDate.plusDays(1);
            }
        }

        return result;
    }

    private String generateLockKey(Long roomId, LocalDateTime startTime, LocalDateTime endTime) {
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm");
        return roomId + ":" + startTime.format(formatter) + ":" + endTime.format(formatter);
    }

    private Booking buildBooking(BookingRequestDTO request, MeetingRoom room) {
        Booking booking = new Booking();
        booking.setRoomId(request.getRoomId());
        booking.setUserId(request.getUserId());
        booking.setTitle(request.getTitle());
        booking.setStartTime(request.getStartTime());
        booking.setEndTime(request.getEndTime());
        booking.setAttendees(request.getAttendees());
        booking.setDescription(request.getDescription());
        booking.setVersion(0);
        return booking;
    }

    private void checkConflict(Long roomId, LocalDateTime startTime,
                               LocalDateTime endTime, Long excludeBookingId) {
        List<Booking> conflicts = bookingMapper.selectConflictBookings(
                roomId, startTime, endTime, excludeBookingId);

        if (!conflicts.isEmpty()) {
            Booking conflict = conflicts.get(0);
            throw new BusinessException(String.format(
                    "该时间段已被预订（%s - %s），请选择其他时间",
                    conflict.getStartTime(), conflict.getEndTime()));
        }
    }

    private void checkRecurringConflicts(Long roomId, List<LocalDateTime> startTimes, Duration duration) {
        for (LocalDateTime startTime : startTimes) {
            LocalDateTime endTime = startTime.plus(duration);
            List<Booking> conflicts = bookingMapper.selectConflictBookings(
                    roomId, startTime, endTime, null);

            if (!conflicts.isEmpty()) {
                Booking conflict = conflicts.get(0);
                throw new BusinessException(String.format(
                        "日期 %s 时间段已被预订（%s - %s），请调整重复预订规则",
                        startTime.toLocalDate(),
                        conflict.getStartTime().toLocalTime(),
                        conflict.getEndTime().toLocalTime()));
            }
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public boolean confirmBooking(Long id) {
        Booking booking = bookingMapper.selectById(id);
        if (booking == null) {
            throw new BusinessException("预订不存在");
        }
        if (booking.getStatus() != BookingStatusEnum.PENDING.getCode()) {
            throw new BusinessException("当前预订状态不支持确认操作");
        }

        int affected = bookingMapper.updateStatus(id, BookingStatusEnum.CONFIRMED.getCode(), booking.getVersion());
        if (affected == 0) {
            throw new BusinessException("预订状态已变更，请刷新后重试");
        }

        notificationService.sendBookingNotification(booking, "CONFIRM");
        return true;
    }

    @Transactional(rollbackFor = Exception.class)
    public boolean cancelBooking(Long id, boolean cancelAllRecurring) {
        Booking booking = bookingMapper.selectById(id);
        if (booking == null) {
            throw new BusinessException("预订不存在");
        }
        if (booking.getStatus() == BookingStatusEnum.CANCELLED.getCode()) {
            throw new BusinessException("预订已取消");
        }

        if (cancelAllRecurring && booking.getIsRecurring() == 1) {
            Long parentId = booking.getRecurringParentId() != null ?
                    booking.getRecurringParentId() : booking.getId();
            List<Booking> recurringBookings = bookingMapper.selectByRecurringParentId(parentId);
            for (Booking b : recurringBookings) {
                bookingMapper.updateStatus(b.getId(), BookingStatusEnum.CANCELLED.getCode(), b.getVersion());
            }
        }

        int affected = bookingMapper.updateStatus(id, BookingStatusEnum.CANCELLED.getCode(), booking.getVersion());
        if (affected == 0) {
            throw new BusinessException("预订状态已变更，请刷新后重试");
        }

        notificationService.sendBookingNotification(booking, "CANCEL");
        return true;
    }

    @Transactional(rollbackFor = Exception.class)
    public Booking updateBooking(Long id, BookingRequestDTO request) {
        Booking existing = bookingMapper.selectById(id);
        if (existing == null) {
            throw new BusinessException("预订不存在");
        }
        if (existing.getStatus() != BookingStatusEnum.PENDING.getCode() &&
                existing.getStatus() != BookingStatusEnum.CONFIRMED.getCode()) {
            throw new BusinessException("当前预订状态不支持修改");
        }

        validateBookingRequest(request);

        if (!request.getRoomId().equals(existing.getRoomId()) ||
                !request.getStartTime().equals(existing.getStartTime()) ||
                !request.getEndTime().equals(existing.getEndTime())) {

            String lockKey = generateLockKey(request.getRoomId(), request.getStartTime(), request.getEndTime());
            String requestId = redisDistributedLock.tryLock(lockKey, LOCK_WAIT_TIME, LOCK_LEASE_TIME, TimeUnit.SECONDS);

            if (requestId == null) {
                throw new BusinessException("系统繁忙，请稍后重试");
            }

            try {
                checkConflict(request.getRoomId(), request.getStartTime(), request.getEndTime(), id);

                existing.setRoomId(request.getRoomId());
                existing.setStartTime(request.getStartTime());
                existing.setEndTime(request.getEndTime());
            } finally {
                redisDistributedLock.unlock(lockKey, requestId);
            }
        }

        existing.setTitle(request.getTitle());
        existing.setAttendees(request.getAttendees());
        existing.setDescription(request.getDescription());

        int affected = bookingMapper.update(existing);
        if (affected == 0) {
            throw new BusinessException("预订已被修改，请刷新后重试");
        }

        return bookingMapper.selectById(id);
    }

    public List<Booking> getRecurringBookings(Long parentId) {
        return bookingMapper.selectByRecurringParentId(parentId);
    }
}
