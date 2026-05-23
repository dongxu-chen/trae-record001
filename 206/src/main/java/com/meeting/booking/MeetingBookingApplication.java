package com.meeting.booking;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.meeting.booking.mapper")
public class MeetingBookingApplication {

    public static void main(String[] args) {
        SpringApplication.run(MeetingBookingApplication.class, args);
    }
}
