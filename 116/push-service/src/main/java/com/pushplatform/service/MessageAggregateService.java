package com.pushplatform.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.pushplatform.entity.MessageAggregate;
import com.pushplatform.mapper.MessageAggregateMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executor;

@Service
public class MessageAggregateService extends ServiceImpl<MessageAggregateMapper, MessageAggregate> {

    private static final Logger logger = LoggerFactory.getLogger(MessageAggregateService.class);

    @Value("${push.aggregate.enabled:true}")
    private boolean aggregateEnabled;

    @Value("${push.aggregate.window-seconds:300}")
    private int defaultWindowSeconds;

    @Value("${push.aggregate.max-messages:10}")
    private int maxMessages;

    @Resource(name = "pushBusinessExecutor")
    private Executor pushBusinessExecutor;

    public void addMessage(String userId, String channel, String title, String content, Map<String, Object> extParams) {
        if (!aggregateEnabled) {
            sendSingleMessage(userId, channel, title, content, extParams);
            return;
        }

        try {
            LambdaQueryWrapper<MessageAggregate> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(MessageAggregate::getUserId, userId)
                    .eq(MessageAggregate::getChannel, channel)
                    .eq(MessageAggregate::getStatus, 0);
            MessageAggregate aggregate = getOne(wrapper);

            Map<String, Object> message = Map.of(
                    "title", title != null ? title : "",
                    "content", content,
                    "extParams", extParams != null ? extParams : Map.of(),
                    "time", LocalDateTime.now().toString()
            );

            if (aggregate == null) {
                aggregate = new MessageAggregate();
                aggregate.setUserId(userId);
                aggregate.setChannel(channel);
                aggregate.setAggregateType("time");
                aggregate.setWindowSeconds(defaultWindowSeconds);
                aggregate.setMessageCount(1);
                aggregate.setMessages(JSON.toJSONString(List.of(message)));
                aggregate.setFirstReceiveTime(LocalDateTime.now());
                aggregate.setLastReceiveTime(LocalDateTime.now());
                aggregate.setStatus(0);
                save(aggregate);
                logger.info("Created new aggregate for user: {}, channel: {}", userId, channel);
            } else {
                List<Map<String, Object>> messages = JSON.parseObject(aggregate.getMessages(), 
                        new TypeReference<List<Map<String, Object>>>() {});
                if (messages == null) {
                    messages = new ArrayList<>();
                }
                messages.add(message);

                if (messages.size() >= maxMessages) {
                    sendAggregatedMessages(aggregate, messages);
                    return;
                }

                aggregate.setMessageCount(messages.size());
                aggregate.setMessages(JSON.toJSONString(messages));
                aggregate.setLastReceiveTime(LocalDateTime.now());
                updateById(aggregate);
                logger.debug("Added message to aggregate for user: {}, count: {}", userId, messages.size());
            }
        } catch (Exception e) {
            logger.error("Add message to aggregate error, user: {}, channel: {}", userId, channel, e);
            sendSingleMessage(userId, channel, title, content, extParams);
        }
    }

    @Scheduled(fixedDelay = 10000)
    public void processExpiredAggregates() {
        if (!aggregateEnabled) {
            return;
        }

        try {
            LambdaQueryWrapper<MessageAggregate> wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(MessageAggregate::getStatus, 0);
            List<MessageAggregate> aggregates = list(wrapper);

            for (MessageAggregate aggregate : aggregates) {
                LocalDateTime expireTime = aggregate.getFirstReceiveTime()
                        .plusSeconds(aggregate.getWindowSeconds());
                
                if (LocalDateTime.now().isAfter(expireTime)) {
                    pushBusinessExecutor.execute(() -> {
                        try {
                            List<Map<String, Object>> messages = JSON.parseObject(aggregate.getMessages(),
                                    new TypeReference<List<Map<String, Object>>>() {});
                            sendAggregatedMessages(aggregate, messages);
                        } catch (Exception e) {
                            logger.error("Process expired aggregate error, id: {}", aggregate.getId(), e);
                        }
                    });
                }
            }
        } catch (Exception e) {
            logger.error("Process expired aggregates error", e);
        }
    }

    private void sendAggregatedMessages(MessageAggregate aggregate, List<Map<String, Object>> messages) {
        try {
            if (messages == null || messages.isEmpty()) {
                removeById(aggregate.getId());
                return;
            }

            String aggregatedContent = buildAggregatedContent(messages);
            String title = messages.size() > 1 ? 
                    "您有" + messages.size() + "条新消息" : 
                    (String) messages.get(0).get("title");

            logger.info("Sending aggregated message, user: {}, count: {}", 
                    aggregate.getUserId(), messages.size());

            aggregate.setStatus(1);
            updateById(aggregate);

        } catch (Exception e) {
            logger.error("Send aggregated message error, id: {}", aggregate.getId(), e);
        }
    }

    private String buildAggregatedContent(List<Map<String, Object>> messages) {
        if (messages.size() == 1) {
            return (String) messages.get(0).get("content");
        }

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < messages.size(); i++) {
            if (i > 0) {
                sb.append("\n\n");
            }
            sb.append(i + 1).append(". ").append(messages.get(i).get("content"));
        }
        return sb.toString();
    }

    private void sendSingleMessage(String userId, String channel, String title, String content, Map<String, Object> extParams) {
        logger.info("Send single message, user: {}, channel: {}, title: {}", userId, channel, title);
    }
}
