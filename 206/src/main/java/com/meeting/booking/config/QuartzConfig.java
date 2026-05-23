package com.meeting.booking.config;

import com.meeting.booking.quartz.BookingStatusUpdateJob;
import org.quartz.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class QuartzConfig {

    @Bean
    public JobDetail bookingStatusUpdateJobDetail() {
        return JobBuilder.newJob(BookingStatusUpdateJob.class)
                .withIdentity("bookingStatusUpdateJob")
                .storeDurably()
                .build();
    }

    @Bean
    public Trigger bookingStatusUpdateTrigger() {
        CronScheduleBuilder scheduleBuilder = CronScheduleBuilder.cronSchedule("0 0/5 * * * ?");

        return TriggerBuilder.newTrigger()
                .forJob(bookingStatusUpdateJobDetail())
                .withIdentity("bookingStatusUpdateTrigger")
                .withSchedule(scheduleBuilder)
                .build();
    }
}
