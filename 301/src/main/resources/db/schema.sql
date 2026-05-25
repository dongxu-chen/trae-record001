CREATE DATABASE IF NOT EXISTS ticket_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ticket_system;

CREATE TABLE IF NOT EXISTS sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    real_name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    department VARCHAR(100),
    position VARCHAR(100),
    available BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_department (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sla (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    ticket_type VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    response_time INT NOT NULL COMMENT '响应时间（分钟）',
    resolution_time INT NOT NULL COMMENT '解决时间（分钟）',
    warning_threshold INT DEFAULT 30 COMMENT '预警阈值（分钟）',
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_type_priority (ticket_type, priority, enabled),
    INDEX idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ticket_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(500),
    ticket_type VARCHAR(50) NOT NULL,
    default_priority VARCHAR(50) NOT NULL,
    default_description TEXT,
    default_assignee_id BIGINT,
    sla_id BIGINT,
    custom_fields TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_enabled (enabled),
    FOREIGN KEY (default_assignee_id) REFERENCES sys_user(id),
    FOREIGN KEY (sla_id) REFERENCES sla(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ticket (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    ticket_no VARCHAR(32) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    ticket_type VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    description TEXT,
    creator_id BIGINT NOT NULL,
    assignee_id BIGINT,
    sla_id BIGINT,
    sla_status VARCHAR(50) DEFAULT 'NORMAL',
    response_deadline DATETIME,
    resolution_deadline DATETIME,
    responded_at DATETIME,
    resolved_at DATETIME,
    resolution VARCHAR(500),
    process_instance_id VARCHAR(64),
    custom_fields TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ticket_no (ticket_no),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_assignee (assignee_id),
    INDEX idx_creator (creator_id),
    INDEX idx_sla_status (sla_status),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (creator_id) REFERENCES sys_user(id),
    FOREIGN KEY (assignee_id) REFERENCES sys_user(id),
    FOREIGN KEY (sla_id) REFERENCES sla(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ticket_relation (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_ticket_id BIGINT NOT NULL,
    target_ticket_id BIGINT NOT NULL,
    relation_type VARCHAR(50) NOT NULL,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source (source_ticket_id),
    INDEX idx_target (target_ticket_id),
    INDEX idx_relation_type (relation_type),
    UNIQUE KEY uk_relation (source_ticket_id, target_ticket_id, relation_type),
    FOREIGN KEY (source_ticket_id) REFERENCES ticket(id),
    FOREIGN KEY (target_ticket_id) REFERENCES ticket(id),
    FOREIGN KEY (created_by) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ticket_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    ticket_id BIGINT NOT NULL,
    from_status VARCHAR(50),
    to_status VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    remark TEXT,
    operator_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ticket (ticket_id),
    INDEX idx_action (action),
    FOREIGN KEY (ticket_id) REFERENCES ticket(id),
    FOREIGN KEY (operator_id) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ticket_comment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    ticket_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    author_id BIGINT NOT NULL,
    internal BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ticket (ticket_id),
    INDEX idx_author (author_id),
    FOREIGN KEY (ticket_id) REFERENCES ticket(id),
    FOREIGN KEY (author_id) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
