package com.ticket.config;

import com.ticket.entity.Sla;
import com.ticket.entity.TicketTemplate;
import com.ticket.entity.User;
import com.ticket.enums.TicketPriority;
import com.ticket.enums.TicketType;
import com.ticket.repository.SlaRepository;
import com.ticket.repository.TicketTemplateRepository;
import com.ticket.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final SlaRepository slaRepository;
    private final TicketTemplateRepository templateRepository;

    @Override
    @Transactional
    public void run(String... args) {
        initUsers();
        initSlas();
        initTemplates();
        log.info("数据初始化完成");
    }

    private void initUsers() {
        if (userRepository.count() == 0) {
            createUser("admin", "123456", "管理员", "admin@example.com", "13800138000", "IT部门", "系统管理员");
            createUser("zhangsan", "123456", "张三", "zhangsan@example.com", "13800138001", "IT部门", "工程师");
            createUser("lisi", "123456", "李四", "lisi@example.com", "13800138002", "IT部门", "工程师");
            createUser("wangwu", "123456", "王五", "wangwu@example.com", "13800138003", "运维部", "运维工程师");
            createUser("zhaoliu", "123456", "赵六", "zhaoliu@example.com", "13800138004", "客服部", "客服代表");
            log.info("初始化用户数据完成");
        }
    }

    private void createUser(String username, String password, String realName, String email,
                            String phone, String department, String position) {
        User user = new User();
        user.setUsername(username);
        user.setPassword("{noop}" + password);
        user.setRealName(realName);
        user.setEmail(email);
        user.setPhone(phone);
        user.setDepartment(department);
        user.setPosition(position);
        user.setAvailable(true);
        userRepository.save(user);
    }

    private void initSlas() {
        if (slaRepository.count() == 0) {
            createSla("紧急事件-SLA", "紧急事件的SLA配置", TicketType.INCIDENT, TicketPriority.URGENT, 15, 60, 10);
            createSla("高优先级事件-SLA", "高优先级事件的SLA配置", TicketType.INCIDENT, TicketPriority.HIGH, 30, 120, 20);
            createSla("中优先级事件-SLA", "中优先级事件的SLA配置", TicketType.INCIDENT, TicketPriority.MEDIUM, 60, 240, 30);
            createSla("低优先级事件-SLA", "低优先级事件的SLA配置", TicketType.INCIDENT, TicketPriority.LOW, 120, 480, 60);
            createSla("服务请求-SLA", "服务请求的SLA配置", TicketType.SERVICE_REQUEST, TicketPriority.MEDIUM, 60, 480, 30);
            createSla("缺陷-SLA", "系统缺陷的SLA配置", TicketType.BUG, TicketPriority.HIGH, 30, 360, 20);
            createSla("咨询-SLA", "技术咨询的SLA配置", TicketType.CONSULTING, TicketPriority.LOW, 120, 720, 60);
            log.info("初始化SLA数据完成");
        }
    }

    private void createSla(String name, String description, TicketType ticketType, TicketPriority priority,
                           int responseTime, int resolutionTime, int warningThreshold) {
        Sla sla = new Sla();
        sla.setName(name);
        sla.setDescription(description);
        sla.setTicketType(ticketType);
        sla.setPriority(priority);
        sla.setResponseTime(responseTime);
        sla.setResolutionTime(resolutionTime);
        sla.setWarningThreshold(warningThreshold);
        sla.setEnabled(true);
        slaRepository.save(sla);
    }

    private void initTemplates() {
        if (templateRepository.count() == 0) {
            User admin = userRepository.findByUsername("admin").orElse(null);
            Sla highIncidentSla = slaRepository.findByTicketTypeAndPriorityAndEnabledTrue(
                    TicketType.INCIDENT, TicketPriority.HIGH).orElse(null);
            Sla serviceRequestSla = slaRepository.findByTicketTypeAndPriorityAndEnabledTrue(
                    TicketType.SERVICE_REQUEST, TicketPriority.MEDIUM).orElse(null);
            Sla bugSla = slaRepository.findByTicketTypeAndPriorityAndEnabledTrue(
                    TicketType.BUG, TicketPriority.HIGH).orElse(null);
            Sla consultingSla = slaRepository.findByTicketTypeAndPriorityAndEnabledTrue(
                    TicketType.CONSULTING, TicketPriority.LOW).orElse(null);

            createTemplate("系统故障模板", "用于报告系统故障的模板", TicketType.INCIDENT, TicketPriority.HIGH,
                    "请描述故障现象：\n1. 发生时间\n2. 影响范围\n3. 复现步骤\n4. 错误截图",
                    admin, highIncidentSla);
            createTemplate("账号申请模板", "用于申请系统账号的模板", TicketType.SERVICE_REQUEST, TicketPriority.MEDIUM,
                    "请填写以下信息：\n1. 申请系统\n2. 申请权限\n3. 使用原因\n4. 预计使用期限",
                    admin, serviceRequestSla);
            createTemplate("Bug反馈模板", "用于反馈系统Bug的模板", TicketType.BUG, TicketPriority.HIGH,
                    "请详细描述Bug：\n1. 问题描述\n2. 复现步骤\n3. 期望结果\n4. 实际结果\n5. 环境信息",
                    admin, bugSla);
            createTemplate("技术咨询模板", "用于技术咨询的模板", TicketType.CONSULTING, TicketPriority.LOW,
                    "请描述您的问题：",
                    admin, consultingSla);
            log.info("初始化工单模板数据完成");
        }
    }

    private void createTemplate(String name, String description, TicketType ticketType, TicketPriority priority,
                                String defaultDescription, User defaultAssignee, Sla sla) {
        TicketTemplate template = new TicketTemplate();
        template.setName(name);
        template.setDescription(description);
        template.setTicketType(ticketType);
        template.setDefaultPriority(priority);
        template.setDefaultDescription(defaultDescription);
        template.setDefaultAssignee(defaultAssignee);
        template.setSla(sla);
        template.setEnabled(true);
        templateRepository.save(template);
    }
}
