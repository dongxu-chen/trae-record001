package com.pushcenter.service;

import com.pushcenter.enums.PushChannel;
import com.pushcenter.model.PushTemplate;
import lombok.extern.slf4j.Slf4j;
import org.apache.velocity.VelocityContext;
import org.apache.velocity.app.VelocityEngine;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.io.StringWriter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class TemplateService {

    @Resource
    private VelocityEngine velocityEngine;

    private final Map<String, PushTemplate> templateCache = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        loadDefaultTemplates();
    }

    public PushTemplate getTemplate(String templateCode) {
        return templateCache.get(templateCode);
    }

    public String renderTitle(PushTemplate template, Map<String, Object> variables) {
        return renderWithVelocity(template.getTitleTemplate(), variables);
    }

    public String renderContent(PushTemplate template, Map<String, Object> variables) {
        return renderWithVelocity(template.getContentTemplate(), variables);
    }

    private String renderWithVelocity(String template, Map<String, Object> variables) {
        if (template == null || template.isEmpty()) {
            return template;
        }

        try {
            VelocityContext context = new VelocityContext();
            if (variables != null) {
                for (Map.Entry<String, Object> entry : variables.entrySet()) {
                    context.put(entry.getKey(), entry.getValue());
                }
            }

            StringWriter writer = new StringWriter();
            velocityEngine.evaluate(context, writer, "TemplateRender", template);

            return writer.toString();
        } catch (Exception e) {
            log.error("Velocity template render failed", e);
            return template;
        }
    }

    public boolean validateVariables(PushTemplate template, Map<String, Object> variables) {
        List<String> required = template.getRequiredVariables();
        if (required == null || required.isEmpty()) {
            return true;
        }

        for (String var : required) {
            if (!containsVariable(variables, var)) {
                log.warn("Missing required variable: {}", var);
                return false;
            }
        }
        return true;
    }

    private boolean containsVariable(Map<String, Object> variables, String varPath) {
        if (variables == null) {
            return false;
        }

        String[] parts = varPath.split("\\.");
        Object current = variables;

        for (String part : parts) {
            if (current instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> map = (Map<String, Object>) current;
                current = map.get(part);
                if (current == null) {
                    return false;
                }
            } else {
                try {
                    current = current.getClass().getMethod("get" + capitalize(part)).invoke(current);
                } catch (Exception e) {
                    return false;
                }
            }
        }
        return true;
    }

    private String capitalize(String str) {
        if (str == null || str.isEmpty()) {
            return str;
        }
        return str.substring(0, 1).toUpperCase() + str.substring(1);
    }

    public void addTemplate(PushTemplate template) {
        templateCache.put(template.getTemplateCode(), template);
        log.info("Template added: {}", template.getTemplateCode());
    }

    public void removeTemplate(String templateCode) {
        templateCache.remove(templateCode);
        log.info("Template removed: {}", templateCode);
    }

    public Collection<PushTemplate> getAllTemplates() {
        return templateCache.values();
    }

    private void loadDefaultTemplates() {
        PushTemplate orderTemplate = PushTemplate.builder()
                .templateCode("ORDER_NOTIFICATION")
                .templateName("订单通知")
                .titleTemplate("您的订单${order.orderId}状态已更新")
                .contentTemplate("尊敬的${user.name}，您的订单${order.orderId}已${order.status}，金额${order.amount}元。\n" +
                        "商品数量：${order.itemCount}件\n" +
                        "#if($order.premium) 尊享会员额外优惠已生效！#end\n" +
                        "感谢您的购买！")
                .supportedChannels(EnumSet.of(PushChannel.EMAIL, PushChannel.SMS, PushChannel.APP_PUSH))
                .defaultChannel(PushChannel.APP_PUSH)
                .requiredVariables(Arrays.asList("order.orderId", "user.name", "order.status", "order.amount"))
                .maxRetryCount(3)
                .enabled(true)
                .build();
        addTemplate(orderTemplate);

        PushTemplate verifyCodeTemplate = PushTemplate.builder()
                .templateCode("VERIFY_CODE")
                .templateName("验证码")
                .titleTemplate("您的验证码")
                .contentTemplate("您的验证码是：${code}，有效期${expireMinutes}分钟。\n" +
                        "#if($operation)当前操作：${operation}#end\n" +
                        "请勿泄露给他人。")
                .supportedChannels(EnumSet.of(PushChannel.SMS, PushChannel.EMAIL))
                .defaultChannel(PushChannel.SMS)
                .requiredVariables(Arrays.asList("code", "expireMinutes"))
                .maxRetryCount(2)
                .enabled(true)
                .build();
        addTemplate(verifyCodeTemplate);

        PushTemplate promotionTemplate = PushTemplate.builder()
                .templateCode("PROMOTION")
                .templateName("营销推广")
                .titleTemplate("${title}")
                .contentTemplate("${content}")
                .supportedChannels(EnumSet.of(PushChannel.EMAIL, PushChannel.DINGTALK, PushChannel.WECHAT_WORK, PushChannel.APP_PUSH))
                .defaultChannel(PushChannel.WECHAT_WORK)
                .requiredVariables(Collections.emptyList())
                .maxRetryCount(2)
                .enabled(true)
                .build();
        addTemplate(promotionTemplate);

        PushTemplate alertTemplate = PushTemplate.builder()
                .templateCode("SYSTEM_ALERT")
                .templateName("系统告警")
                .titleTemplate("系统告警：${alert.level} - ${alert.service}")
                .contentTemplate("告警时间：${alert.time}\n" +
                        "告警级别：${alert.level}\n" +
                        "服务名称：${alert.service}\n" +
                        "服务器：${alert.server}\n" +
                        "告警内容：${alert.message}\n" +
                        "#if($alert.duration)持续时间：${alert.duration}秒#end")
                .supportedChannels(EnumSet.of(PushChannel.DINGTALK, PushChannel.WECHAT_WORK, PushChannel.SMS))
                .defaultChannel(PushChannel.DINGTALK)
                .requiredVariables(Arrays.asList("alert.level", "alert.time", "alert.message", "alert.server", "alert.service"))
                .maxRetryCount(3)
                .enabled(true)
                .build();
        addTemplate(alertTemplate);

        log.info("Loaded {} default templates with Velocity engine support", templateCache.size());
    }
}
