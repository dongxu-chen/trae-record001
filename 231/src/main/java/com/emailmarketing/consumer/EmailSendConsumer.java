package com.emailmarketing.consumer;

import com.emailmarketing.config.RabbitMQConfig;
import com.emailmarketing.dto.EmailSendMessage;
import com.emailmarketing.entity.EmailSendLog;
import com.emailmarketing.service.EmailSendLogService;
import com.emailmarketing.service.EmailSendService;
import com.emailmarketing.service.EmailTaskService;
import com.rabbitmq.client.Channel;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.support.AmqpHeaders;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.time.LocalDateTime;

@Slf4j
@Component
public class EmailSendConsumer {

    @Autowired
    private EmailSendService emailSendService;

    @Autowired
    private EmailTaskService emailTaskService;

    @Autowired
    private EmailSendLogService sendLogService;

    @RabbitListener(queues = RabbitMQConfig.EMAIL_QUEUE)
    public void handleMessage(EmailSendMessage message, Channel channel,
                              @Header(AmqpHeaders.DELIVERY_TAG) long deliveryTag) throws IOException {
        try {
            if (emailTaskService.isUnsubscribed(message.getToEmail())) {
                log.info("Recipient unsubscribed, skipping email: {}", message.getToEmail());
                EmailSendLog skipLog = new EmailSendLog();
                skipLog.setId(message.getSendLogId());
                skipLog.setSendStatus(0);
                skipLog.setErrorMsg("收件人已退订，跳过发送");
                skipLog.setUnsubscribed(1);
                skipLog.setUnsubscribeTime(LocalDateTime.now());
                sendLogService.updateById(skipLog);
                channel.basicAck(deliveryTag, false);
                return;
            }

            boolean success = emailSendService.sendEmail(message);
            
            if (success) {
                emailTaskService.incrementSuccessCount(message.getTaskId());
            } else {
                emailTaskService.incrementFailCount(message.getTaskId());
            }
            
            channel.basicAck(deliveryTag, false);
        } catch (Exception e) {
            log.error("Failed to send email to: {}", message.getToEmail(), e);
            EmailSendLog errorLog = new EmailSendLog();
            errorLog.setId(message.getSendLogId());
            errorLog.setSendStatus(2);
            errorLog.setErrorMsg(e.getMessage());
            sendLogService.updateById(errorLog);
            
            emailTaskService.incrementFailCount(message.getTaskId());
            channel.basicNack(deliveryTag, false, false);
        }
    }
}
