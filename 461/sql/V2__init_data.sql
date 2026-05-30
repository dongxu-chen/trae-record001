-- 插入示例版本数据
INSERT INTO api_version (name, version, status, description, base_path) VALUES
('用户服务', 'v1', 'ACTIVE', '用户服务v1版本', '/api/v1'),
('用户服务', 'v2', 'ACTIVE', '用户服务v2版本，新增字段', '/api/v2'),
('订单服务', 'v1', 'ACTIVE', '订单服务v1版本', '/api/v1'),
('订单服务', 'v2', 'DEPRECATED', '订单服务v2版本，待废弃', '/api/v2');

-- 插入示例路由规则
INSERT INTO routing_rule (api_name, strategy, weight_v1, weight_v2) VALUES
('用户服务', 'WEIGHTED', 30, 70),
('订单服务', 'PATH', 0, 100);
