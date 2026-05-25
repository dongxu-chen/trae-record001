package com.survey.service;

import com.survey.config.RabbitMQConfig;
import com.survey.dto.VoteMessage;
import com.rabbitmq.client.Channel;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.support.AmqpHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.stereotype.Service;

import java.io.IOException;

@Slf4j
@Service
@RequiredArgsConstructor
public class StatsMessageConsumer {

    private final StatsService statsService;

    @RabbitListener(queues = RabbitMQConfig.STATS_QUEUE, containerFactory = "rabbitListenerContainerFactory")
    public void consumeVoteMessage(VoteMessage message, Channel channel,
                                   @Header(AmqpHeaders.DELIVERY_TAG) long tag) {
        try {
            log.info("Received vote message for survey: {}", message.getSurveyId());

            statsService.updateStats(message.getSurveyId(), message.getAnswers());

            channel.basicAck(tag, false);
            log.info("Processed vote message successfully");
        } catch (Exception e) {
            log.error("Failed to process vote message", e);
            try {
                channel.basicNack(tag, false, true);
            } catch (IOException ex) {
                log.error("Failed to nack message", ex);
            }
        }
    }
}
