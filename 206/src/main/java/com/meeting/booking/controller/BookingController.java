package com.meeting.booking.controller;

import com.meeting.booking.common.PageResult;
import com.meeting.booking.common.Result;
import com.meeting.booking.dto.BookingQueryDTO;
import com.meeting.booking.dto.BookingRequestDTO;
import com.meeting.booking.entity.Booking;
import com.meeting.booking.service.BookingService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/bookings")
public class BookingController {

    @Autowired
    private BookingService bookingService;

    @GetMapping("/{id}")
    public Result<Booking> getById(@PathVariable Long id) {
        return Result.success(bookingService.getById(id));
    }

    @GetMapping
    public Result<PageResult<Booking>> list(BookingQueryDTO query) {
        return Result.success(bookingService.list(query));
    }

    @GetMapping("/user/{userId}")
    public Result<List<Booking>> getByUserId(@PathVariable Long userId) {
        return Result.success(bookingService.getByUserId(userId));
    }

    @GetMapping("/recurring/{parentId}")
    public Result<List<Booking>> getRecurringBookings(@PathVariable Long parentId) {
        return Result.success(bookingService.getRecurringBookings(parentId));
    }

    @PostMapping
    public Result<Booking> create(@Validated @RequestBody BookingRequestDTO request) {
        return Result.success(bookingService.createBooking(request));
    }

    @PutMapping("/{id}")
    public Result<Booking> update(@PathVariable Long id, @Validated @RequestBody BookingRequestDTO request) {
        return Result.success(bookingService.updateBooking(id, request));
    }

    @PostMapping("/{id}/confirm")
    public Result<Boolean> confirm(@PathVariable Long id) {
        return Result.success(bookingService.confirmBooking(id));
    }

    @PostMapping("/{id}/cancel")
    public Result<Boolean> cancel(
            @PathVariable Long id,
            @RequestParam(defaultValue = "false") boolean cancelAllRecurring) {
        return Result.success(bookingService.cancelBooking(id, cancelAllRecurring));
    }
}
