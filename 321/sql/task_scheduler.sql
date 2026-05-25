-- 任务调度系统数据库脚本
CREATE DATABASE IF NOT EXISTS task_scheduler DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE task_scheduler;

-- 执行器信息表
DROP TABLE IF EXISTS `executor_info`;
CREATE TABLE `executor_info` (
    `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `executor_name` varchar(100) NOT NULL COMMENT '执行器名称',
    `executor_address` varchar(255) NOT NULL COMMENT '执行器地址（ip:port）',
    `app_name` varchar(100) NOT NULL COMMENT '应用名称',
    `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：0-离线，1-在线',
    `heartbeat_time` datetime DEFAULT NULL COMMENT '最后心跳时间',
    `register_time` datetime DEFAULT NULL COMMENT '注册时间',
    `description` varchar(500) DEFAULT NULL COMMENT '描述',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_executor_address` (`executor_address`),
    KEY `idx_app_name` (`app_name`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='执行器信息表';

-- 任务信息表
DROP TABLE IF EXISTS `task_info`;
CREATE TABLE `task_info` (
    `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `task_name` varchar(100) NOT NULL COMMENT '任务名称',
    `task_group` varchar(100) NOT NULL DEFAULT 'DEFAULT' COMMENT '任务分组',
    `task_type` tinyint NOT NULL DEFAULT '1' COMMENT '任务类型：1-Cron定时任务，2-DAG依赖任务',
    `cron_expression` varchar(50) DEFAULT NULL COMMENT 'Cron表达式（Cron任务用）',
    `handler` varchar(255) NOT NULL COMMENT '任务处理器（bean名称或类名）',
    `params` text COMMENT '任务参数JSON',
    `executor_route_strategy` tinyint NOT NULL DEFAULT '1' COMMENT '执行器路由策略：1-轮询，2-随机，3-一致性哈希',
    `task_timeout` int NOT NULL DEFAULT '300' COMMENT '任务超时时间（秒）',
    `max_retry_count` int NOT NULL DEFAULT '0' COMMENT '最大重试次数',
    `retry_interval` int NOT NULL DEFAULT '60' COMMENT '重试间隔（秒）',
    `priority` tinyint NOT NULL DEFAULT '5' COMMENT '优先级：1-最高，10-最低，默认5',
    `sharding_total` int NOT NULL DEFAULT '1' COMMENT '分片总数',
    `sharding_param` varchar(500) DEFAULT NULL COMMENT '分片参数配置JSON',
    `dag_dependencies` varchar(500) DEFAULT NULL COMMENT 'DAG依赖任务ID列表，逗号分隔',
    `status` tinyint NOT NULL DEFAULT '1' COMMENT '状态：0-停止，1-运行中',
    `last_execute_time` datetime DEFAULT NULL COMMENT '上次执行时间',
    `next_execute_time` datetime DEFAULT NULL COMMENT '下次执行时间',
    `description` varchar(500) DEFAULT NULL COMMENT '描述',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_name_group` (`task_name`,`task_group`),
    KEY `idx_task_type` (`task_type`),
    KEY `idx_status` (`status`),
    KEY `idx_next_execute_time` (`next_execute_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务信息表';

-- 任务执行日志表
DROP TABLE IF EXISTS `task_log`;
CREATE TABLE `task_log` (
    `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `task_id` bigint NOT NULL COMMENT '任务ID',
    `task_name` varchar(100) NOT NULL COMMENT '任务名称',
    `task_group` varchar(100) NOT NULL COMMENT '任务分组',
    `handler` varchar(255) NOT NULL COMMENT '任务处理器',
    `params` text COMMENT '任务参数',
    `executor_address` varchar(255) DEFAULT NULL COMMENT '执行器地址',
    `execute_type` tinyint NOT NULL DEFAULT '1' COMMENT '执行类型：1-正常执行，2-重试执行，3-手动触发',
    `trigger_code` int NOT NULL DEFAULT '0' COMMENT '调度结果：0-成功，非0-失败',
    `trigger_msg` varchar(1000) DEFAULT NULL COMMENT '调度结果描述',
    `trigger_time` datetime DEFAULT NULL COMMENT '调度触发时间',
    `execute_code` int DEFAULT NULL COMMENT '执行结果：0-成功，非0-失败',
    `execute_msg` text COMMENT '执行结果描述',
    `execute_start_time` datetime DEFAULT NULL COMMENT '执行开始时间',
    `execute_end_time` datetime DEFAULT NULL COMMENT '执行结束时间',
    `sharding_index` int DEFAULT '-1' COMMENT '分片索引，-1表示未分片',
    `sharding_total` int DEFAULT '1' COMMENT '分片总数',
    `retry_count` int NOT NULL DEFAULT '0' COMMENT '当前重试次数',
    `parent_log_id` bigint DEFAULT NULL COMMENT '父任务日志ID（DAG任务用）',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_task_id` (`task_id`),
    KEY `idx_trigger_time` (`trigger_time`),
    KEY `idx_trigger_code` (`trigger_code`),
    KEY `idx_execute_code` (`execute_code`),
    KEY `idx_parent_log_id` (`parent_log_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行日志表';

-- 任务分片信息表
DROP TABLE IF EXISTS `task_shard`;
CREATE TABLE `task_shard` (
    `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `task_id` bigint NOT NULL COMMENT '任务ID',
    `log_id` bigint NOT NULL COMMENT '任务日志ID',
    `shard_index` int NOT NULL COMMENT '分片索引',
    `shard_total` int NOT NULL COMMENT '分片总数',
    `shard_param` varchar(500) DEFAULT NULL COMMENT '分片参数',
    `executor_address` varchar(255) DEFAULT NULL COMMENT '分配的执行器地址',
    `status` tinyint NOT NULL DEFAULT '0' COMMENT '状态：0-待执行，1-执行中，2-执行成功，3-执行失败',
    `retry_count` int NOT NULL DEFAULT '0' COMMENT '重试次数',
    `execute_start_time` datetime DEFAULT NULL COMMENT '执行开始时间',
    `execute_end_time` datetime DEFAULT NULL COMMENT '执行结束时间',
    `execute_msg` text COMMENT '执行结果',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_log_shard` (`log_id`,`shard_index`),
    KEY `idx_task_id` (`task_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务分片信息表';

-- 初始化数据
INSERT INTO `executor_info` (`executor_name`, `executor_address`, `app_name`, `status`, `description`) VALUES
('示例执行器1', '127.0.0.1:9999', 'demo-executor', 1, '示例执行器');

INSERT INTO `task_info` (`task_name`, `task_group`, `task_type`, `cron_expression`, `handler`, `task_timeout`, `max_retry_count`, `description`) VALUES
('测试Cron任务', 'DEFAULT', 1, '0/30 * * * * ?', 'demoTask', 300, 2, '每30秒执行一次的测试任务');
