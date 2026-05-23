package com.meeting.booking.controller;

import com.meeting.booking.common.Result;
import com.meeting.booking.dto.ApprovalRequestDTO;
import com.meeting.booking.entity.ApprovalRecord;
import com.meeting.booking.service.ApprovalService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/approvals")
public class ApprovalController {

    @Autowired
    private ApprovalService approvalService;

    @GetMapping("/{id}")
    public Result<ApprovalRecord> getById(@PathVariable Long id) {
        return Result.success(approvalService.getById(id));
    }

    @GetMapping("/booking/{bookingId}")
    public Result<List<ApprovalRecord>> getByBookingId(@PathVariable Long bookingId) {
        return Result.success(approvalService.getByBookingId(bookingId));
    }

    @GetMapping("/approver/{approverId}")
    public Result<List<ApprovalRecord>> getByApproverId(
            @PathVariable Long approverId,
            @RequestParam(required = false) Integer status) {
        return Result.success(approvalService.getByApproverId(approverId, status));
    }

    @GetMapping("/pending")
    public Result<List<ApprovalRecord>> getPendingApprovals() {
        return Result.success(approvalService.getPendingApprovals());
    }

    @PostMapping("/approve")
    public Result<ApprovalRecord> approve(@Validated @RequestBody ApprovalRequestDTO request) {
        return Result.success(approvalService.approve(request));
    }
}
