package com.platform.points.task;

import com.platform.points.service.PointsExpireService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class PointsExpireTask {

    @Autowired
    private PointsExpireService pointsExpireService;

    @Scheduled(cron = "0 0 2 * * ?")
    public void expirePoints() {
        log.info("开始执行积分过期清理定时任务");
        try {
            pointsExpireService.batchExpire();
            log.info("积分过期清理定时任务执行完成");
        } catch (Exception e) {
            log.error("积分过期清理定时任务执行异常", e);
        }
    }
}
