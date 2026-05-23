package com.meeting.booking.mapper;

import com.meeting.booking.entity.Notification;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface NotificationMapper {

    Notification selectById(@Param("id") Long id);

    List<Notification> selectByUserId(@Param("userId") Long userId, @Param("isRead") Integer isRead);

    int countUnread(@Param("userId") Long userId);

    int insert(Notification notification);

    int markAsRead(@Param("id") Long id);

    int markAllAsRead(@Param("userId") Long userId);

    int batchInsert(@Param("list") List<Notification> notifications);
}
