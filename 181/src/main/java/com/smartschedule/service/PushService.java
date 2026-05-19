package com.smartschedule.service;

import com.smartschedule.entity.Notification;

public interface PushService {
    boolean sendNotification(Notification notification);
}
