package com.meeting.booking.service;

import com.meeting.booking.common.ApprovalStatusEnum;
import com.meeting.booking.common.BookingStatusEnum;
import com.meeting.booking.dto.ApprovalRequestDTO;
import com.meeting.booking.entity.ApprovalRecord;
import com.meeting.booking.entity.Booking;
import com.meeting.booking.exception.BusinessException;
import com.meeting.booking.mapper.ApprovalRecordMapper;
import com.meeting.booking.mapper.BookingMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
public class ApprovalService {

    @Autowired
    private ApprovalRecordMapper approvalRecordMapper;

    @Autowired
    private BookingMapper bookingMapper;

    @Autowired
    private NotificationService notificationService;

    public static final int APPROVAL_THRESHOLD = 10;

    public ApprovalRecord getById(Long id) {
        return approvalRecordMapper.selectById(id);
    }

    public List<ApprovalRecord> getByBookingId(Long bookingId) {
        return approvalRecordMapper.selectByBookingId(bookingId);
    }

    public List<ApprovalRecord> getByApproverId(Long approverId, Integer status) {
        return approvalRecordMapper.selectByApproverId(approverId, status);
    }

    public List<ApprovalRecord> getPendingApprovals() {
        return approvalRecordMapper.selectPendingApprovals();
    }

    @Transactional(rollbackFor = Exception.class)
    public void createApprovalRecord(Booking booking) {
        ApprovalRecord record = new ApprovalRecord();
        record.setBookingId(booking.getId());
        record.setStatus(ApprovalStatusEnum.PENDING.getCode());
        approvalRecordMapper.insert(record);
        log.info("Created approval record for booking: {}", booking.getId());
    }

    @Transactional(rollbackFor = Exception.class)
    public ApprovalRecord approve(ApprovalRequestDTO request) {
        ApprovalRecord record = approvalRecordMapper.selectById(request.getApprovalId());
        if (record == null) {
            throw new BusinessException("审批记录不存在");
        }
        if (record.getStatus() != ApprovalStatusEnum.PENDING.getCode()) {
            throw new BusinessException("该审批已处理，无法重复审批");
        }

        Booking booking = bookingMapper.selectById(record.getBookingId());
        if (booking == null) {
            throw new BusinessException("关联的预订不存在");
        }

        approvalRecordMapper.updateStatus(
                request.getApprovalId(),
                request.getApproverId(),
                request.getStatus(),
                request.getRemark()
        );

        if (ApprovalStatusEnum.APPROVED.getCode().equals(request.getStatus())) {
            bookingMapper.updateStatus(
                    booking.getId(),
                    BookingStatusEnum.CONFIRMED.getCode(),
                    booking.getVersion()
            );
            booking.setApprovalStatus(ApprovalStatusEnum.APPROVED.getCode());
            notificationService.sendApprovalNotification(booking, true, request.getRemark());
        } else if (ApprovalStatusEnum.REJECTED.getCode().equals(request.getStatus())) {
            bookingMapper.updateStatus(
                    booking.getId(),
                    BookingStatusEnum.CANCELLED.getCode(),
                    booking.getVersion()
            );
            booking.setApprovalStatus(ApprovalStatusEnum.REJECTED.getCode());
            notificationService.sendApprovalNotification(booking, false, request.getRemark());
        }

        return approvalRecordMapper.selectById(request.getApprovalId());
    }

    public boolean needsApproval(int attendees) {
        return attendees >= APPROVAL_THRESHOLD;
    }
}
