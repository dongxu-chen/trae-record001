USE ticket_system;

INSERT IGNORE INTO sys_user (username, password, real_name, email, phone, department, position, available) VALUES
('admin', '{noop}123456', '管理员', 'admin@example.com', '13800138000', 'IT部门', '系统管理员', TRUE),
('zhangsan', '{noop}123456', '张三', 'zhangsan@example.com', '13800138001', 'IT部门', '工程师', TRUE),
('lisi', '{noop}123456', '李四', 'lisi@example.com', '13800138002', 'IT部门', '工程师', TRUE),
('wangwu', '{noop}123456', '王五', 'wangwu@example.com', '13800138003', '运维部', '运维工程师', TRUE),
('zhaoliu', '{noop}123456', '赵六', 'zhaoliu@example.com', '13800138004', '客服部', '客服代表', TRUE);

INSERT IGNORE INTO sla (name, description, ticket_type, priority, response_time, resolution_time, warning_threshold, enabled) VALUES
('紧急事件-SLA', '紧急事件的SLA配置', 'INCIDENT', 'URGENT', 15, 60, 10, TRUE),
('高优先级事件-SLA', '高优先级事件的SLA配置', 'INCIDENT', 'HIGH', 30, 120, 20, TRUE),
('中优先级事件-SLA', '中优先级事件的SLA配置', 'INCIDENT', 'MEDIUM', 60, 240, 30, TRUE),
('低优先级事件-SLA', '低优先级事件的SLA配置', 'INCIDENT', 'LOW', 120, 480, 60, TRUE),
('服务请求-SLA', '服务请求的SLA配置', 'SERVICE_REQUEST', 'MEDIUM', 60, 480, 30, TRUE),
('缺陷-SLA', '系统缺陷的SLA配置', 'BUG', 'HIGH', 30, 360, 20, TRUE),
('咨询-SLA', '技术咨询的SLA配置', 'CONSULTING', 'LOW', 120, 720, 60, TRUE);

INSERT IGNORE INTO ticket_template (name, description, ticket_type, default_priority, default_description, default_assignee_id, sla_id, enabled) VALUES
('系统故障模板', '用于报告系统故障的模板', 'INCIDENT', 'HIGH', '请描述故障现象：\n1. 发生时间\n2. 影响范围\n3. 复现步骤\n4. 错误截图', NULL, 2, TRUE),
('账号申请模板', '用于申请系统账号的模板', 'SERVICE_REQUEST', 'MEDIUM', '请填写以下信息：\n1. 申请系统\n2. 申请权限\n3. 使用原因\n4. 预计使用期限', NULL, 5, TRUE),
('Bug反馈模板', '用于反馈系统Bug的模板', 'BUG', 'HIGH', '请详细描述Bug：\n1. 问题描述\n2. 复现步骤\n3. 期望结果\n4. 实际结果\n5. 环境信息', NULL, 6, TRUE),
('技术咨询模板', '用于技术咨询的模板', 'CONSULTING', 'LOW', '请描述您的问题：', NULL, 7, TRUE);
