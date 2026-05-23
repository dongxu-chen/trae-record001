package com.meeting.booking.service;

import com.meeting.booking.entity.Booking;
import com.meeting.booking.entity.Notification;
import com.meeting.booking.mapper.NotificationMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
public class NotificationService {

    @Autowired
    private NotificationMapper notificationMapper;

    public Notification getById(Long id) {
        return notificationMapper.selectById(id);
    }

    public List<Notification> getByUserId(Long userId, Integer isRead) {
        return notificationMapper.selectByUserId(userId, isRead);
    }

    public int countUnread(Long userId) {
        return notificationMapper.countUnread(userId);
    }

    public boolean markAsRead(Long id) {
        return notificationMapper.markAsRead(id) > 0;
    }

    public boolean markAllAsRead(Long userId) {
        return notificationMapper.markAllAsRead(userId) > 0;
    }

    public void sendApprovalNotification(Booking booking, boolean approved, String remark) {
        Notification notification = new Notification();
        notification.setUserId(booking.getUserId());
        notification.setType("APPROVAL");
        notification.setRelatedId(booking.getId());

        if (approved) {
            notification.setTitle("预订审批通过");
            notification.setContent(String.format(
                    "您的预订【%s】已审批通过，时间：%s - %s",
                    booking.getTitle(), booking.getStartTime(), booking.getEndTime()
            ));
        } else {
            notification.setTitle("预订审批拒绝");
            notification.setContent(String.format(
                    "您的预订【%s】已被拒绝，原因：%s，时间：%s - %s",
                    booking.getTitle(), remark != null ? remark : "无",
                    booking.getStartTime(), booking.getEndTime()
            ));
        }

        notificationMapper.insert(notification);
        log.info("Sent approval notification to user: {}", booking.getUserId());
    }

    public void sendBookingNotification(Booking booking, String action) {
        Notification notification = new Notification();
        notification.setUserId(booking.getUserId());
        notification.setType("BOOKING");
        notification.setRelatedId(booking.getId());

        switch (action) {
            case "CREATE":
                notification.setTitle("预订创建成功");
                notification.setContent(String.format(
                        "您的预订【%s】已创建成功，等待确认。时间：%s - %s",
                        booking.getTitle(), booking.getStartTime(), booking.getEndTime()
                ));
                break;
            case "CONFIRM":
                notification.setTitle("预订已确认");
                notification.setContent(String.format(
                        "您的预订【%s】已确认。时间：%s - %s",
                        booking.getTitle(), booking.getStartTime(), booking.getEndTime()
                ));
                break;
            case "CANCEL":
                notification.setTitle("预订已取消");
                notification.setContent(String.format(
                        "您的预订【%s】已取消。",
                        booking.getTitle()
                ));
                break;
            case "PENDING_APPROVAL":
                notification.setTitle("预订待审批");
                notification.setContent(String.format(
                        "您的预订【%s】因参会人数较多，已提交审批，请耐心等待。时间：%s - %s",
                        booking.getTitle(), booking.getStartTime(), booking.getEndTime()
                ));
                break;
        }

        notificationMapper.insert(notification);
        log.info("Sent booking notification to user: {}", booking.getUserId());
    }
}
