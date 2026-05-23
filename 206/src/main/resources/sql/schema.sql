CREATE DATABASE IF NOT EXISTS meeting_booking DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE meeting_booking;

DROP TABLE IF EXISTS booking;
DROP TABLE IF EXISTS meeting_room_equipment;
DROP TABLE IF EXISTS equipment;
DROP TABLE IF EXISTS meeting_room;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    name VARCHAR(50) NOT NULL COMMENT '姓名',
    email VARCHAR(100) COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    department VARCHAR(100) COMMENT '部门',
    status TINYINT DEFAULT 1 COMMENT '状态：1-正常，0-禁用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username),
    INDEX idx_department (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

CREATE TABLE meeting_room (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '会议室ID',
    name VARCHAR(100) NOT NULL COMMENT '会议室名称',
    location VARCHAR(200) NOT NULL COMMENT '位置',
    capacity INT NOT NULL COMMENT '容纳人数',
    description VARCHAR(500) COMMENT '描述',
    status TINYINT DEFAULT 1 COMMENT '状态：1-可用，0-不可用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_capacity (capacity),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会议室表';

CREATE TABLE equipment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '设备ID',
    name VARCHAR(100) NOT NULL COMMENT '设备名称',
    code VARCHAR(50) NOT NULL UNIQUE COMMENT '设备编码',
    type VARCHAR(50) COMMENT '设备类型：PROJECTOR-投影仪，WHITEBOARD-白板，TV-电视，MIC-麦克风，CAMERA-摄像头',
    description VARCHAR(500) COMMENT '描述',
    status TINYINT DEFAULT 1 COMMENT '状态：1-可用，0-不可用',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_type (type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备表';

CREATE TABLE meeting_room_equipment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    room_id BIGINT NOT NULL COMMENT '会议室ID',
    equipment_id BIGINT NOT NULL COMMENT '设备ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_room_equipment (room_id, equipment_id),
    FOREIGN KEY (room_id) REFERENCES meeting_room(id) ON DELETE CASCADE,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会议室设备关联表';

CREATE TABLE booking (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '预订ID',
    room_id BIGINT NOT NULL COMMENT '会议室ID',
    user_id BIGINT NOT NULL COMMENT '预订用户ID',
    title VARCHAR(200) NOT NULL COMMENT '会议主题',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME NOT NULL COMMENT '结束时间',
    attendees INT NOT NULL DEFAULT 0 COMMENT '参会人数',
    description VARCHAR(500) COMMENT '会议描述',
    status TINYINT DEFAULT 1 COMMENT '状态：0-已取消，1-待确认，2-已确认，3-已完成，4-待审批',
    need_approval TINYINT DEFAULT 0 COMMENT '是否需要审批：0-否，1-是',
    approval_status TINYINT DEFAULT 0 COMMENT '审批状态：0-待审批，1-已通过，2-已拒绝',
    is_recurring TINYINT DEFAULT 0 COMMENT '是否重复预订：0-否，1-是',
    recurring_rule VARCHAR(200) COMMENT '重复规则：WEEKLY-每周，DAILY-每天',
    recurring_days VARCHAR(50) COMMENT '重复日期：1,2,3,4,5,6,7（周几）',
    recurring_end_date DATE COMMENT '重复结束日期',
    recurring_parent_id BIGINT COMMENT '重复预订父ID',
    version INT DEFAULT 0 COMMENT '乐观锁版本号',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_room_status_time (room_id, status, start_time, end_time),
    INDEX idx_user_status_time (user_id, status, start_time),
    INDEX idx_status_time (status, start_time),
    INDEX idx_approval_status (approval_status, need_approval),
    INDEX idx_recurring (is_recurring, recurring_parent_id),
    INDEX idx_create_time (create_time),
    FOREIGN KEY (room_id) REFERENCES meeting_room(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预订表';

CREATE TABLE approval_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '审批记录ID',
    booking_id BIGINT NOT NULL COMMENT '预订ID',
    approver_id BIGINT COMMENT '审批人ID',
    status TINYINT DEFAULT 0 COMMENT '审批状态：0-待审批，1-已通过，2-已拒绝',
    remark VARCHAR(500) COMMENT '审批备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_booking_id (booking_id),
    INDEX idx_approver_id (approver_id),
    INDEX idx_status (status),
    FOREIGN KEY (booking_id) REFERENCES booking(id),
    FOREIGN KEY (approver_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审批记录表';

CREATE TABLE notification (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '通知ID',
    user_id BIGINT NOT NULL COMMENT '接收用户ID',
    type VARCHAR(50) NOT NULL COMMENT '通知类型：APPROVAL-审批通知，BOOKING-预订通知',
    title VARCHAR(200) NOT NULL COMMENT '通知标题',
    content VARCHAR(1000) COMMENT '通知内容',
    related_id BIGINT COMMENT '关联ID',
    is_read TINYINT DEFAULT 0 COMMENT '是否已读：0-未读，1-已读',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_user_read (user_id, is_read),
    INDEX idx_create_time (create_time),
    FOREIGN KEY (user_id) REFERENCES user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知表';

INSERT INTO user (username, name, email, phone, department) VALUES
('zhangsan', '张三', 'zhangsan@company.com', '13800138001', '技术部'),
('lisi', '李四', 'lisi@company.com', '13800138002', '产品部'),
('wangwu', '王五', 'wangwu@company.com', '13800138003', '市场部');

INSERT INTO meeting_room (name, location, capacity, description) VALUES
('多功能厅A', '1楼东侧', 50, '大型会议室，适合全员大会'),
('会议室B', '2楼北侧', 20, '中型会议室，适合部门会议'),
('会议室C', '2楼南侧', 10, '小型会议室，适合小组讨论'),
('洽谈室D', '3楼东侧', 6, '洽谈室，适合商务洽谈'),
('培训室E', '3楼西侧', 30, '培训室，适合内部培训');

INSERT INTO equipment (name, code, type, description) VALUES
('投影仪1号', 'PJ001', 'PROJECTOR', '高清投影仪'),
('投影仪2号', 'PJ002', 'PROJECTOR', '激光投影仪'),
('智能白板1号', 'WB001', 'WHITEBOARD', '交互式电子白板'),
('智能白板2号', 'WB002', 'WHITEBOARD', '普通白板'),
('电视1号', 'TV001', 'TV', '65寸智能电视'),
('麦克风1号', 'MIC001', 'MIC', '无线麦克风系统'),
('摄像头1号', 'CAM001', 'CAMERA', '高清视频会议摄像头');

INSERT INTO meeting_room_equipment (room_id, equipment_id) VALUES
(1, 1), (1, 3), (1, 5), (1, 6), (1, 7),
(2, 2), (2, 4), (2, 5),
(3, 1), (3, 4),
(4, 5),
(5, 2), (5, 3), (5, 6), (5, 7);
