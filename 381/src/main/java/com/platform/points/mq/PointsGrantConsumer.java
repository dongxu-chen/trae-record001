package com.platform.points.mq;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.platform.points.dto.PointsGrantDTO;
import com.platform.points.service.PointsService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RocketMQMessageListener(
        topic = "${points.mq.topic.points-grant}",
        consumerGroup = "${spring.rocketmq.consumer.group}"
)
public class PointsGrantConsumer implements RocketMQListener<String> {

    @Autowired
    private PointsService pointsService;

    @Override
    public void onMessage(String message) {
        log.info("收到积分发放消息: {}", message);
        try {
            JSONObject json = JSON.parseObject(message);
            PointsGrantDTO dto = json.toJavaObject(PointsGrantDTO.class);
            pointsService.processGrant(dto);
            log.info("积分发放处理成功, userId: {}, points: {}", dto.getUserId(), dto.getPoints());
        } catch (Exception e) {
            log.error("积分发放处理失败: {}", message, e);
        }
    }
}
