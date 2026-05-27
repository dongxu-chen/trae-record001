package com.platform.points.mq;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.platform.points.service.PointsExpireService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RocketMQMessageListener(
        topic = "${points.mq.topic.points-expire}",
        consumerGroup = "${spring.rocketmq.consumer.group}"
)
public class PointsExpireConsumer implements RocketMQListener<String> {

    @Autowired
    private PointsExpireService pointsExpireService;

    @Override
    public void onMessage(String message) {
        log.info("收到积分过期消息: {}", message);
        try {
            JSONObject json = JSON.parseObject(message);
            Long userId = json.getLong("userId");
            Integer points = json.getInteger("points");
            pointsExpireService.processExpire(userId, points);
            log.info("积分过期处理成功, userId: {}, points: {}", userId, points);
        } catch (Exception e) {
            log.error("积分过期处理失败: {}", message, e);
        }
    }
}
