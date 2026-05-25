CREATE DATABASE IF NOT EXISTS property_repair DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE property_repair;

INSERT INTO sys_user (username, password, real_name, phone, role, status, create_time) VALUES
('admin', 'admin123', '系统管理员', '13800138000', 'ADMIN', 1, NOW()),
('owner1', 'owner123', '业主张三', '13800138001', 'OWNER', 1, NOW()),
('owner2', 'owner123', '业主李四', '13800138002', 'OWNER', 1, NOW()),
('worker1', 'worker123', '维修工小王', '13800138003', 'WORKER', 1, NOW()),
('worker2', 'worker123', '维修工小李', '13800138004', 'WORKER', 1, NOW()),
('worker3', 'worker123', '维修工老赵', '13800138005', 'WORKER', 1, NOW());

INSERT INTO repair_worker (worker_id, skills, current_workload, avg_rating, total_orders, work_area, longitude, latitude, status, create_time) VALUES
(4, '水电,管道', 0, 4.8, 25, '东城区', 116.4074, 39.9042, 1, NOW()),
(5, '电器,空调', 0, 4.5, 32, '西城区', 116.3647, 39.9128, 1, NOW()),
(6, '土建,门窗', 0, 4.2, 18, '朝阳区', 116.4434, 39.9261, 1, NOW());

INSERT INTO repair_type (type_name, description, estimated_hours, priority, remind_minutes, is_emergency, status, create_time) VALUES
('水电维修', '水管、电路相关维修', 2, 2, 30, 1, 1, NOW()),
('电器维修', '家电、照明设备维修', 2, 2, 60, 0, 1, NOW()),
('管道维修', '下水道、排污管道维修', 3, 3, 15, 1, 1, NOW()),
('空调维修', '空调设备维修保养', 2, 2, 45, 0, 1, NOW()),
('土建维修', '墙面、地面维修', 4, 1, 60, 0, 1, NOW()),
('门窗维修', '门窗、锁具维修', 2, 1, 60, 0, 1, NOW());

INSERT INTO spare_part (part_code, part_name, specification, category, unit, unit_price, stock_quantity, locked_quantity, safe_stock, location, description, status, create_time) VALUES
('SP001', 'PPR水管', '20mm', '水电材料', '根', 15.50, 100, 0, 20, 'A区01架', 'PPR热水管', 1, NOW()),
('SP002', '水龙头', '铜质冷热水', '五金配件', '个', 45.00, 50, 0, 10, 'A区02架', '厨房水龙头', 1, NOW()),
('SP003', '灯泡', 'LED 15W', '电气配件', '个', 12.00, 200, 0, 50, 'B区01架', '节能LED灯泡', 1, NOW()),
('SP004', '空调滤芯', '通用型', '空调配件', '个', 35.00, 80, 0, 20, 'C区01架', '空调过滤网', 1, NOW()),
('SP005', '门锁', '防盗门锁芯', '五金配件', '套', 85.00, 30, 0, 10, 'A区03架', 'C级防盗门锁', 1, NOW()),
('SP006', 'PVC排水管', '50mm', '管道材料', '根', 28.00, 60, 0, 15, 'D区01架', 'PVC排水管材', 1, NOW());
