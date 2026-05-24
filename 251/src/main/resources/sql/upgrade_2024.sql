-- 为已有数据库添加新字段的升级脚本

-- 1. 为coupon表添加group_code字段
ALTER TABLE coupon ADD COLUMN group_code VARCHAR(50) COMMENT '优惠券互斥分组编码' AFTER per_user_limit;
ALTER TABLE coupon ADD INDEX idx_group_code (group_code);

-- 2. 为order_info表添加coupon_ids字段
ALTER TABLE order_info ADD COLUMN coupon_ids VARCHAR(255) COMMENT '使用的优惠券ID列表，逗号分隔' AFTER coupon_id;

-- 示例数据：添加互斥分组的优惠券
-- INSERT INTO coupon (name, code, type, discount_amount, min_amount, total_count, per_user_limit, group_code, valid_start_time, valid_end_time, status)
-- VALUES 
-- ('新人专享券1', 'NEW1', 1, 50.00, 200.00, 1000, 1, 'NEW_USER', '2024-01-01 00:00:00', '2024-12-31 23:59:59', 1),
-- ('新人专享券2', 'NEW2', 1, 100.00, 500.00, 1000, 1, 'NEW_USER', '2024-01-01 00:00:00', '2024-12-31 23:59:59', 1),
-- ('满减券A', 'DISCOUNT_A', 1, 30.00, 100.00, 5000, 1, 'DISCOUNT_GROUP', '2024-01-01 00:00:00', '2024-12-31 23:59:59', 1),
-- ('满减券B', 'DISCOUNT_B', 2, 10.00, 100.00, 5000, 1, 'DISCOUNT_GROUP', '2024-01-01 00:00:00', '2024-12-31 23:59:59', 1);
