package com.meeting.booking.quartz;

import com.meeting.booking.common.BookingStatusEnum;
import com.meeting.booking.entity.Booking;
import com.meeting.booking.mapper.BookingMapper;
import com.meeting.booking.util.RedisDistributedLock;
import lombok.extern.slf4j.Slf4j;
import org.quartz.DisallowConcurrentExecution;
import org.quartz.JobExecutionContext;
import org.quartz.PersistJobDataAfterExecution;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.quartz.QuartzJobBean;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@PersistJobDataAfterExecution
@DisallowConcurrentExecution
public class BookingStatusUpdateJob extends QuartzJobBean {

    @Autowired
    private BookingMapper bookingMapper;

    @Autowired
    private RedisDistributedLock redisDistributedLock;

    private static final String LOCK_KEY = "job:booking:status:update";
    private static final long LOCK_LEASE_TIME = 300;

    @Override
    protected void executeInternal(JobExecutionContext context) {
        String requestId = redisDistributedLock.tryLock(LOCK_KEY, 0, LOCK_LEASE_TIME, TimeUnit.SECONDS);
        if (requestId == null) {
            log.info("Booking status update job is already running, skip this execution");
            return;
        }

        try {
            log.info("Starting booking status update job at {}", LocalDateTime.now());
            updateCompletedBookings();
            log.info("Booking status update job completed at {}", LocalDateTime.now());
        } catch (Exception e) {
            log.error("Booking status update job failed", e);
        } finally {
            redisDistributedLock.unlock(LOCK_KEY, requestId);
        }
    }

    private void updateCompletedBookings() {
        LocalDateTime now = LocalDateTime.now();

        com.meeting.booking.dto.BookingQueryDTO query = new com.meeting.booking.dto.BookingQueryDTO();
        query.setStatus(BookingStatusEnum.CONFIRMED.getCode());
        query.setPageNum(1);
        query.setPageSize(100);

        List<Booking> bookings = bookingMapper.selectList(query);

        int updatedCount = 0;
        for (Booking booking : bookings) {
            if (booking.getEndTime().isBefore(now)) {
                int affected = bookingMapper.updateStatus(
                        booking.getId(),
                        BookingStatusEnum.COMPLETED.getCode(),
                        booking.getVersion()
                );
                if (affected > 0) {
                    updatedCount++;
                    log.info("Updated booking {} status to COMPLETED", booking.getId());
                }
            }
        }

        log.info("Updated {} bookings to COMPLETED status", updatedCount);
    }
}
