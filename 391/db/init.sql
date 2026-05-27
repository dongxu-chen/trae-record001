-- =====================================================
-- 定时任务依赖管理系统 - 数据库初始化脚本
-- =====================================================

CREATE DATABASE IF NOT EXISTS task_scheduler DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE task_scheduler;

-- =====================================================
-- 任务定义表：存储所有可调度的任务及其元数据
-- =====================================================
DROP TABLE IF EXISTS `task_definitions`;
CREATE TABLE `task_definitions` (
    `task_id`           VARCHAR(128)  NOT NULL COMMENT '任务唯一标识',
    `task_name`         VARCHAR(256)  NOT NULL COMMENT '任务显示名称',
    `task_type`         VARCHAR(64)   NOT NULL DEFAULT 'celery' COMMENT '任务类型: celery/airflow/http',
    `task_module`       VARCHAR(512)  NOT NULL COMMENT '任务模块路径',
    `task_function`     VARCHAR(128)  NOT NULL COMMENT '任务函数名',
    `description`       TEXT          NULL COMMENT '任务描述',
    `queue`             VARCHAR(64)   NOT NULL DEFAULT 'celery' COMMENT 'Celery队列',
    `priority`          INT           NOT NULL DEFAULT 5 COMMENT '优先级 1-10',
    `max_retries`       INT           NOT NULL DEFAULT 3 COMMENT '最大重试次数',
    `retry_delay_sec`   INT           NOT NULL DEFAULT 60 COMMENT '基础重试延迟(秒)',
    `retry_backoff`     TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用指数退避',
    `retry_backoff_max_sec` INT       NOT NULL DEFAULT 3600 COMMENT '指数退避最大延迟(秒)',
    `timeout_sec`       INT           NOT NULL DEFAULT 3600 COMMENT '任务超时时间(秒)',
    `enabled`           TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用',
    `resource_profile`  VARCHAR(32)   NOT NULL DEFAULT 'MEDIUM' COMMENT '资源规格: SMALL/MEDIUM/LARGE/XLARGE',
    `estimated_cpu_percent` FLOAT     NOT NULL DEFAULT 20.0 COMMENT '预估CPU占比',
    `estimated_memory_mb` INT         NOT NULL DEFAULT 512 COMMENT '预估内存(MB)',
    `estimated_duration_sec` INT      NOT NULL DEFAULT 300 COMMENT '预估时长(秒)',
    `business_criticality` VARCHAR(16) NOT NULL DEFAULT 'MEDIUM' COMMENT '业务重要性: CRITICAL/HIGH/MEDIUM/LOW',
    `created_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`task_id`),
    KEY `idx_queue` (`queue`),
    KEY `idx_enabled` (`enabled`),
    KEY `idx_criticality` (`business_criticality`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务定义表';

-- =====================================================
-- 任务依赖关系表：定义DAG的有向边 (支持增量检测)
-- =====================================================
DROP TABLE IF EXISTS `task_dependencies`;
CREATE TABLE `task_dependencies` (
    `id`                BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    `dag_id`            VARCHAR(128)  NOT NULL COMMENT '所属DAG ID',
    `upstream_task_id`  VARCHAR(128)  NOT NULL COMMENT '上游任务ID',
    `downstream_task_id` VARCHAR(128) NOT NULL COMMENT '下游任务ID',
    `dependency_type`   VARCHAR(32)   NOT NULL DEFAULT 'all_success' COMMENT '依赖类型: all_success/any_success/all_done',
    `is_detected`       TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否已被增量检测',
    `detected_at`       DATETIME      NULL COMMENT '增量检测时间',
    `source`            VARCHAR(32)   NOT NULL DEFAULT 'MANUAL' COMMENT '来源: MANUAL/AUTO_DETECT/INCREMENTAL_CHECK',
    `created_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_dag` (`dag_id`),
    KEY `idx_upstream` (`upstream_task_id`),
    KEY `idx_downstream` (`downstream_task_id`),
    KEY `idx_is_detected` (`is_detected`),
    UNIQUE KEY `uk_edge` (`dag_id`, `upstream_task_id`, `downstream_task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务依赖关系表';

-- =====================================================
-- DAG定义表：存储DAG的元信息
-- =====================================================
DROP TABLE IF EXISTS `dag_definitions`;
CREATE TABLE `dag_definitions` (
    `dag_id`            VARCHAR(128)  NOT NULL COMMENT 'DAG唯一标识',
    `dag_name`          VARCHAR(256)  NOT NULL COMMENT 'DAG显示名称',
    `description`       TEXT          NULL COMMENT 'DAG描述',
    `schedule_interval` VARCHAR(64)   NOT NULL DEFAULT '@daily' COMMENT '调度间隔',
    `owner`             VARCHAR(64)   NOT NULL DEFAULT 'admin' COMMENT '负责人',
    `enabled`           TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用',
    `max_active_runs`   INT           NOT NULL DEFAULT 1 COMMENT '最大并行运行数',
    `catchup`           TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否追赶调度',
    `tags`              VARCHAR(512)  NULL COMMENT '标签(逗号分隔)',
    `created_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`dag_id`),
    KEY `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='DAG定义表';

-- =====================================================
-- 任务执行日志表：集中记录所有任务执行记录
-- =====================================================
DROP TABLE IF EXISTS `task_execution_logs`;
CREATE TABLE `task_execution_logs` (
    `log_id`            BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    `dag_id`            VARCHAR(128)  NOT NULL,
    `task_id`           VARCHAR(128)  NOT NULL,
    `run_id`            VARCHAR(128)  NOT NULL COMMENT 'DAG运行ID',
    `celery_task_id`    VARCHAR(128)  NULL COMMENT 'Celery任务UUID',
    `execution_date`    DATETIME      NOT NULL COMMENT '执行开始时间',
    `duration_sec`      FLOAT         NULL COMMENT '执行耗时(秒)',
    `status`            VARCHAR(32)   NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/RUNNING/SUCCESS/FAILURE/RETRY/REVOKED',
    `attempt`           INT           NOT NULL DEFAULT 1 COMMENT '第几次尝试',
    `worker_name`       VARCHAR(128)  NULL COMMENT '执行Worker名称',
    `input_params`      JSON          NULL COMMENT '任务输入参数',
    `output_result`     JSON          NULL COMMENT '任务输出结果',
    `error_message`     TEXT          NULL COMMENT '错误信息',
    `error_traceback`   MEDIUMTEXT    NULL COMMENT '错误堆栈',
    `retry_count`       INT           NOT NULL DEFAULT 0 COMMENT '已重试次数',
    `next_retry_time`   DATETIME      NULL COMMENT '下次重试时间(指数退避)',
    `is_dead_letter`    TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否进入死信队列',
    `created_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`log_id`),
    KEY `idx_dag_task` (`dag_id`, `task_id`),
    KEY `idx_celery_id` (`celery_task_id`),
    KEY `idx_status` (`status`),
    KEY `idx_exec_date` (`execution_date`),
    KEY `idx_dead_letter` (`is_dead_letter`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务执行日志表';

-- =====================================================
-- 死信队列表：存储超过重试次数的失败任务 (支持TTL)
-- =====================================================
DROP TABLE IF EXISTS `dead_letter_queue`;
CREATE TABLE `dead_letter_queue` (
    `dlq_id`            BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    `celery_task_id`    VARCHAR(128)  NOT NULL COMMENT 'Celery任务UUID',
    `dag_id`            VARCHAR(128)  NOT NULL,
    `task_id`           VARCHAR(128)  NOT NULL,
    `run_id`            VARCHAR(128)  NOT NULL,
    `task_module`       VARCHAR(512)  NOT NULL COMMENT '任务模块路径',
    `task_function`     VARCHAR(128)  NOT NULL COMMENT '任务函数名',
    `input_params`      JSON          NULL COMMENT '任务输入参数',
    `error_message`     TEXT          NULL COMMENT '错误信息',
    `error_traceback`   MEDIUMTEXT    NULL COMMENT '错误堆栈',
    `total_retries`     INT           NOT NULL DEFAULT 0 COMMENT '总重试次数',
    `original_queued_at` DATETIME     NOT NULL COMMENT '原始入队时间',
    `dead_lettered_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '进入死信时间',
    `ttl_seconds`       INT           NOT NULL DEFAULT 604800 COMMENT 'TTL存活时间(秒)，默认7天',
    `expires_at`        DATETIME      NULL COMMENT '过期时间',
    `status`            VARCHAR(32)   NOT NULL DEFAULT 'PENDING' COMMENT '状态: PENDING/REPROCESSED/DISCARDED',
    `reprocessed_at`    DATETIME      NULL COMMENT '重处理时间',
    `reprocessed_by`    VARCHAR(64)   NULL COMMENT '重处理人',
    `notes`             TEXT          NULL COMMENT '备注',
    PRIMARY KEY (`dlq_id`),
    KEY `idx_celery_id` (`celery_task_id`),
    KEY `idx_status` (`status`),
    KEY `idx_dead_lettered_at` (`dead_lettered_at`),
    KEY `idx_expires_at` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='死信队列表';

-- =====================================================
-- 任务重跑记录表：记录任务重跑操作
-- =====================================================
DROP TABLE IF EXISTS `task_rerun_records`;
CREATE TABLE `task_rerun_records` (
    `rerun_id`          BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    `original_log_id`   BIGINT UNSIGNED NOT NULL COMMENT '原始执行日志ID',
    `original_celery_id` VARCHAR(128) NOT NULL COMMENT '原始Celery任务ID',
    `dag_id`            VARCHAR(128)  NOT NULL,
    `task_id`           VARCHAR(128)  NOT NULL,
    `run_id`            VARCHAR(128)  NOT NULL,
    `rerun_type`        VARCHAR(32)   NOT NULL DEFAULT 'MANUAL' COMMENT '重跑类型: MANUAL/AUTO_RETRY/DLQ_REPROCESS',
    `rerun_celery_id`   VARCHAR(128)  NULL COMMENT '新Celery任务ID',
    `rerun_status`      VARCHAR(32)   NOT NULL DEFAULT 'PENDING' COMMENT '重跑状态',
    `triggered_by`      VARCHAR(64)   NOT NULL DEFAULT 'system' COMMENT '触发人',
    `triggered_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`rerun_id`),
    KEY `idx_original_log` (`original_log_id`),
    KEY `idx_dag_task` (`dag_id`, `task_id`),
    KEY `idx_triggered_at` (`triggered_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务重跑记录表';

-- =====================================================
-- Worker节点表：记录集群中Worker节点的实时资源状态
-- =====================================================
DROP TABLE IF EXISTS `worker_nodes`;
CREATE TABLE `worker_nodes` (
    `worker_id`         VARCHAR(128)  NOT NULL COMMENT 'Worker节点ID',
    `hostname`          VARCHAR(256)  NOT NULL COMMENT '主机名',
    `queues`            VARCHAR(512)  NOT NULL DEFAULT 'celery' COMMENT '监听队列(逗号分隔)',
    `total_cpu_cores`   INT           NOT NULL DEFAULT 4 COMMENT 'CPU核心总数',
    `total_memory_mb`   INT           NOT NULL DEFAULT 8192 COMMENT '总内存(MB)',
    `current_cpu_percent` FLOAT       NOT NULL DEFAULT 0.0 COMMENT '当前CPU占比',
    `current_memory_mb` INT           NOT NULL DEFAULT 0 COMMENT '当前已用内存(MB)',
    `active_task_count` INT           NOT NULL DEFAULT 0 COMMENT '当前活跃任务数',
    `max_concurrent_tasks` INT        NOT NULL DEFAULT 8 COMMENT '最大并发任务数',
    `status`            VARCHAR(32)   NOT NULL DEFAULT 'ONLINE' COMMENT '状态: ONLINE/OFFLINE/BUSY',
    `last_heartbeat`    DATETIME      NULL COMMENT '最近心跳时间',
    `region`            VARCHAR(64)   NULL COMMENT '区域',
    `labels`            VARCHAR(512)  NULL COMMENT '标签(逗号分隔)',
    `created_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`worker_id`),
    KEY `idx_status` (`status`),
    KEY `idx_queues` (`queues`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Worker节点资源监控表';

-- =====================================================
-- 资源分配表：记录智能调度决策的资源分配
-- =====================================================
DROP TABLE IF EXISTS `resource_allocations`;
CREATE TABLE `resource_allocations` (
    `id`                BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    `celery_task_id`    VARCHAR(128)  NOT NULL COMMENT 'Celery任务ID',
    `dag_id`            VARCHAR(128)  NOT NULL,
    `task_id`           VARCHAR(128)  NOT NULL,
    `worker_id`         VARCHAR(128)  NOT NULL COMMENT '分配的Worker',
    `queue_name`        VARCHAR(64)   NOT NULL COMMENT '使用的队列',
    `allocated_cpu_percent` FLOAT     NOT NULL DEFAULT 0.0 COMMENT '分配CPU占比',
    `allocated_memory_mb` INT         NOT NULL DEFAULT 0 COMMENT '分配内存(MB)',
    `allocation_strategy` VARCHAR(32) NOT NULL DEFAULT 'SMART' COMMENT '策略: SMART/RR/QUEUE_PINNED',
    `decision_reason`   TEXT          NULL COMMENT '决策原因',
    `allocation_time`   DATETIME      NOT NULL COMMENT '分配时间',
    `release_time`      DATETIME      NULL COMMENT '释放时间',
    `status`            VARCHAR(32)   NOT NULL DEFAULT 'ALLOCATED' COMMENT 'ALLOCATED/RELEASED/FAILED',
    PRIMARY KEY (`id`),
    KEY `idx_celery_id` (`celery_task_id`),
    KEY `idx_worker_id` (`worker_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务资源分配记录表';

-- =====================================================
-- 任务血缘表：记录任务的数据输入/输出血缘
-- =====================================================
DROP TABLE IF EXISTS `task_lineage`;
CREATE TABLE `task_lineage` (
    `lineage_id`        BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    `dag_id`            VARCHAR(128)  NOT NULL,
    `task_id`           VARCHAR(128)  NOT NULL,
    `run_id`            VARCHAR(128)  NOT NULL,
    `source_dataset`    VARCHAR(512)  NULL COMMENT '输入数据集',
    `target_dataset`    VARCHAR(512)  NULL COMMENT '输出数据集',
    `transformation_type` VARCHAR(64) NULL COMMENT '转换类型: ETL/TRANSFORM/AGGREGATE',
    `row_count`         BIGINT        NULL COMMENT '数据行数',
    `data_hash`         VARCHAR(128)  NULL COMMENT '数据哈希(用于变更检测)',
    `parent_lineage_ids` VARCHAR(1024) NULL COMMENT '上游血缘ID(逗号分隔)',
    `execution_time`    DATETIME      NOT NULL COMMENT '执行时间',
    `metadata`          JSON          NULL COMMENT '扩展元数据',
    PRIMARY KEY (`lineage_id`),
    KEY `idx_dag_task` (`dag_id`, `task_id`),
    KEY `idx_run_id` (`run_id`),
    KEY `idx_source_dataset` (`source_dataset`),
    KEY `idx_target_dataset` (`target_dataset`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务数据血缘表';

-- =====================================================
-- 影响分析表：记录任务失败影响分析结果
-- =====================================================
DROP TABLE IF EXISTS `impact_analyses`;
CREATE TABLE `impact_analyses` (
    `analysis_id`       BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    `dag_id`            VARCHAR(128)  NOT NULL,
    `task_id`           VARCHAR(128)  NOT NULL,
    `analysis_type`     VARCHAR(32)   NOT NULL DEFAULT 'FAILURE_PREDICTION' COMMENT '分析类型',
    `failure_probability` FLOAT       NOT NULL DEFAULT 0.0 COMMENT '失败概率',
    `affected_downstream_count` INT   NOT NULL DEFAULT 0 COMMENT '受影响下游任务数',
    `affected_task_list` TEXT          NULL COMMENT '受影响任务列表',
    `affected_dataset_list` TEXT        NULL COMMENT '受影响数据集列表',
    `estimated_recovery_minutes` INT  NULL COMMENT '预估恢复时间(分钟)',
    `business_impact_level` VARCHAR(16) NOT NULL DEFAULT 'LOW' COMMENT '业务影响级别: CRITICAL/HIGH/MEDIUM/LOW',
    `recommended_actions` TEXT         NULL COMMENT '建议行动',
    `analysis_time`     DATETIME      NOT NULL COMMENT '分析时间',
    `metadata`          JSON          NULL COMMENT '扩展元数据',
    PRIMARY KEY (`analysis_id`),
    KEY `idx_dag_task` (`dag_id`, `task_id`),
    KEY `idx_analysis_time` (`analysis_time`),
    KEY `idx_impact_level` (`business_impact_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务影响分析表';

-- =====================================================
-- 调度决策表：记录智能调度决策历史
-- =====================================================
DROP TABLE IF EXISTS `scheduling_decisions`;
CREATE TABLE `scheduling_decisions` (
    `decision_id`       BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    `task_id`           VARCHAR(128)  NOT NULL,
    `dag_id`            VARCHAR(128)  NOT NULL,
    `worker_id`         VARCHAR(128)  NULL COMMENT '目标Worker',
    `queue_name`        VARCHAR(64)   NULL COMMENT '目标队列',
    `decision_type`     VARCHAR(32)   NOT NULL DEFAULT 'SCHEDULE' COMMENT 'SCHEDULE/DEFER/REJECT',
    `priority_score`    FLOAT         NOT NULL DEFAULT 0.0 COMMENT '优先级评分',
    `resource_score`    FLOAT         NOT NULL DEFAULT 0.0 COMMENT '资源适配评分',
    `business_score`    FLOAT         NOT NULL DEFAULT 0.0 COMMENT '业务重要性评分',
    `waiting_minutes`   INT           NOT NULL DEFAULT 0 COMMENT '已等待分钟',
    `reason`            TEXT          NULL COMMENT '决策理由',
    `decision_time`     DATETIME      NOT NULL COMMENT '决策时间',
    `status`            VARCHAR(32)   NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/EXECUTED/REJECTED',
    PRIMARY KEY (`decision_id`),
    KEY `idx_task_id` (`task_id`),
    KEY `idx_decision_time` (`decision_time`),
    KEY `idx_decision_type` (`decision_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能调度决策记录表';

-- =====================================================
-- 示例数据
-- =====================================================

INSERT INTO `dag_definitions` (`dag_id`, `dag_name`, `description`, `schedule_interval`, `owner`, `max_active_runs`, `tags`)
VALUES
    ('etl_data_pipeline', 'ETL数据处理管道', '每日ETL数据处理流程', '@daily', 'admin', 1, 'etl,data,incremental'),
    ('report_generation', '报表生成流水线', '每日报表自动生成流程', '@daily', 'admin', 1, 'report,analytics,incremental'),
    ('ml_training_pipeline', 'ML模型训练流水线', '机器学习模型训练流程', '@weekly', 'admin', 1, 'ml,training,incremental');

INSERT INTO `task_definitions` (`task_id`, `task_name`, `task_type`, `task_module`, `task_function`, `queue`, `max_retries`, `retry_delay_sec`, `retry_backoff`, `retry_backoff_max_sec`, `description`, `resource_profile`, `estimated_cpu_percent`, `estimated_memory_mb`, `estimated_duration_sec`, `business_criticality`)
VALUES
    ('extract_data', '数据抽取', 'celery', 'celery_app.tasks.etl', 'extract_data', 'etl', 3, 30, 1, 600, '从数据源抽取原始数据', 'MEDIUM', 25.0, 512, 120, 'HIGH'),
    ('transform_data', '数据转换', 'celery', 'celery_app.tasks.etl', 'transform_data', 'etl', 3, 30, 1, 600, '对抽取的数据进行转换清洗', 'LARGE', 50.0, 1024, 300, 'HIGH'),
    ('load_data', '数据加载', 'celery', 'celery_app.tasks.etl', 'load_data', 'etl', 3, 60, 1, 1200, '将转换后的数据加载到目标存储', 'LARGE', 40.0, 1024, 600, 'CRITICAL'),
    ('generate_daily_report', '生成日报', 'celery', 'celery_app.tasks.report', 'generate_daily_report', 'report', 3, 30, 1, 600, '生成每日运营报表', 'MEDIUM', 20.0, 512, 180, 'MEDIUM'),
    ('generate_weekly_report', '生成周报', 'celery', 'celery_app.tasks.report', 'generate_weekly_report', 'report', 3, 60, 1, 1200, '生成每周汇总报表', 'LARGE', 40.0, 1024, 600, 'MEDIUM'),
    ('send_report_notification', '发送报表通知', 'celery', 'celery_app.tasks.report', 'send_report_notification', 'report', 3, 10, 1, 300, '发送报表完成通知邮件', 'SMALL', 10.0, 256, 30, 'LOW'),
    ('prepare_training_data', '准备训练数据', 'celery', 'celery_app.tasks.ml', 'prepare_training_data', 'ml', 3, 60, 1, 1200, '准备机器学习训练数据', 'LARGE', 50.0, 1024, 600, 'HIGH'),
    ('train_model', '训练模型', 'celery', 'celery_app.tasks.ml', 'train_model', 'ml', 2, 300, 1, 3600, '训练机器学习模型', 'XLARGE', 80.0, 2048, 1800, 'CRITICAL'),
    ('evaluate_model', '评估模型', 'celery', 'celery_app.tasks.ml', 'evaluate_model', 'ml', 3, 30, 1, 600, '评估模型性能', 'MEDIUM', 30.0, 768, 300, 'HIGH'),
    ('deploy_model', '部署模型', 'celery', 'celery_app.tasks.ml', 'deploy_model', 'ml', 2, 120, 1, 1800, '将模型部署到生产环境', 'MEDIUM', 25.0, 512, 120, 'CRITICAL');

INSERT INTO `task_dependencies` (`dag_id`, `upstream_task_id`, `downstream_task_id`, `dependency_type`, `is_detected`, `detected_at`, `source`)
VALUES
    ('etl_data_pipeline', 'extract_data', 'transform_data', 'all_success', 1, NOW(), 'AUTO_DETECT'),
    ('etl_data_pipeline', 'transform_data', 'load_data', 'all_success', 1, NOW(), 'AUTO_DETECT'),
    ('etl_data_pipeline', 'load_data', 'generate_daily_report', 'all_success', 1, NOW(), 'AUTO_DETECT'),
    ('report_generation', 'generate_daily_report', 'generate_weekly_report', 'all_success', 1, NOW(), 'AUTO_DETECT'),
    ('report_generation', 'generate_weekly_report', 'send_report_notification', 'all_success', 1, NOW(), 'AUTO_DETECT'),
    ('ml_training_pipeline', 'prepare_training_data', 'train_model', 'all_success', 1, NOW(), 'AUTO_DETECT'),
    ('ml_training_pipeline', 'train_model', 'evaluate_model', 'all_success', 1, NOW(), 'AUTO_DETECT'),
    ('ml_training_pipeline', 'evaluate_model', 'deploy_model', 'all_success', 1, NOW(), 'AUTO_DETECT');
