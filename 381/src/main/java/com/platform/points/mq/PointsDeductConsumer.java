package com.platform.points.mq;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.platform.points.dto.PointsDeductDTO;
import com.platform.points.service.PointsService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RocketMQMessageListener(
        topic = "${points.mq.topic.points-deduct}",
        consumerGroup = "${spring.rocketmq.consumer.group}"
)
public class PointsDeductConsumer implements RocketMQListener<String> {

    @Autowired
    private PointsService pointsService;

    @Override
    public void onMessage(String message) {
        log.info("收到积分扣减消息: {}", message);
        try {
            JSONObject json = JSON.parseObject(message);
            PointsDeductDTO dto = json.toJavaObject(PointsDeductDTO.class);
            pointsService.processDeduct(dto);
            log.info("积分扣减处理成功, userId: {}, points: {}", dto.getUserId(), dto.getPoints());
        } catch (Exception e) {
            log.error("积分扣减处理失败: {}", message, e);
        }
    }
}
