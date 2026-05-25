CREATE DATABASE IF NOT EXISTS sms_platform DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE sms_platform;

DROP TABLE IF EXISTS `sms_signature`;
CREATE TABLE `sms_signature` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `signature_name` varchar(50) NOT NULL COMMENT '签名名称',
    `signature_content` varchar(100) NOT NULL COMMENT '签名内容',
    `sms_type` tinyint(4) NOT NULL COMMENT '短信类型 1验证码 2通知 3营销',
    `channel_code` tinyint(4) NOT NULL COMMENT '通道编码 1阿里云 2腾讯云',
    `status` tinyint(4) NOT NULL DEFAULT 1 COMMENT '状态 0禁用 1启用',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除 0未删除 1已删除',
    PRIMARY KEY (`id`),
    KEY `idx_sms_type` (`sms_type`),
    KEY `idx_channel_code` (`channel_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短信签名表';

DROP TABLE IF EXISTS `sms_template`;
CREATE TABLE `sms_template` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `template_code` varchar(50) NOT NULL COMMENT '模板编码',
    `template_name` varchar(100) NOT NULL COMMENT '模板名称',
    `template_content` varchar(500) NOT NULL COMMENT '模板内容',
    `sms_type` tinyint(4) NOT NULL COMMENT '短信类型 1验证码 2通知 3营销',
    `channel_code` tinyint(4) NOT NULL COMMENT '通道编码 1阿里云 2腾讯云',
    `external_template_id` varchar(100) DEFAULT NULL COMMENT '运营商模板ID',
    `variable_names` varchar(200) DEFAULT NULL COMMENT '变量名列表，逗号分隔',
    `status` tinyint(4) NOT NULL DEFAULT 1 COMMENT '状态 0禁用 1启用',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除 0未删除 1已删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_template_code` (`template_code`),
    KEY `idx_sms_type` (`sms_type`),
    KEY `idx_channel_code` (`channel_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短信模板表';

DROP TABLE IF EXISTS `sms_channel_config`;
CREATE TABLE `sms_channel_config` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `channel_code` tinyint(4) NOT NULL COMMENT '通道编码 1阿里云 2腾讯云',
    `channel_name` varchar(50) NOT NULL COMMENT '通道名称',
    `is_master` tinyint(4) NOT NULL DEFAULT 0 COMMENT '是否主通道 0否 1是',
    `weight` int(11) NOT NULL DEFAULT 100 COMMENT '权重',
    `max_send_per_second` int(11) NOT NULL DEFAULT 100 COMMENT '每秒最大发送量',
    `max_send_per_minute` int(11) NOT NULL DEFAULT 5000 COMMENT '每分钟最大发送量',
    `max_send_per_hour` int(11) NOT NULL DEFAULT 30000 COMMENT '每小时最大发送量',
    `token_bucket_capacity` int(11) NOT NULL DEFAULT 1000 COMMENT '令牌桶容量',
    `token_bucket_rate` int(11) NOT NULL DEFAULT 100 COMMENT '令牌生成速率(个/秒)',
    `receipt_timeout_seconds` int(11) NOT NULL DEFAULT 300 COMMENT '回执超时时间(秒)',
    `max_receipt_timeout_count` int(11) NOT NULL DEFAULT 5 COMMENT '最大连续回执超时次数',
    `status` tinyint(4) NOT NULL DEFAULT 1 COMMENT '状态 0禁用 1启用',
    `is_healthy` tinyint(4) NOT NULL DEFAULT 1 COMMENT '健康状态 0不健康 1健康',
    `fail_count` int(11) NOT NULL DEFAULT 0 COMMENT '连续失败次数',
    `receipt_timeout_count` int(11) NOT NULL DEFAULT 0 COMMENT '连续回执超时次数',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除 0未删除 1已删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_channel_code` (`channel_code`),
    KEY `idx_is_master` (`is_master`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短信通道配置表';

DROP TABLE IF EXISTS `sms_send_record`;
CREATE TABLE `sms_send_record` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `serial_no` varchar(64) NOT NULL COMMENT '发送流水号',
    `mobile` varchar(20) NOT NULL COMMENT '手机号',
    `sms_type` tinyint(4) NOT NULL COMMENT '短信类型 1验证码 2通知 3营销',
    `signature_id` bigint(20) DEFAULT NULL COMMENT '签名ID',
    `template_id` bigint(20) DEFAULT NULL COMMENT '模板ID',
    `template_code` varchar(50) DEFAULT NULL COMMENT '模板编码',
    `channel_code` tinyint(4) NOT NULL COMMENT '通道编码 1阿里云 2腾讯云',
    `send_content` varchar(1000) DEFAULT NULL COMMENT '发送内容',
    `variable_params` varchar(500) DEFAULT NULL COMMENT '变量参数JSON',
    `status` tinyint(4) NOT NULL DEFAULT 0 COMMENT '发送状态 0待发送 1成功 2失败 3黑名单 4限流 5回执超时 6内容违规 7时段限制',
    `error_msg` varchar(500) DEFAULT NULL COMMENT '错误信息',
    `external_serial_no` varchar(100) DEFAULT NULL COMMENT '运营商流水号',
    `send_time` datetime DEFAULT NULL COMMENT '发送时间',
    `receipt_status` tinyint(4) DEFAULT NULL COMMENT '回执状态 0待回执 1回执成功 2回执失败 3回执超时',
    `receipt_time` datetime DEFAULT NULL COMMENT '回执时间',
    `receipt_expire_time` datetime DEFAULT NULL COMMENT '回执超时时间',
    `receipt_content` varchar(500) DEFAULT NULL COMMENT '回执内容',
    `content_security_status` tinyint(4) DEFAULT NULL COMMENT '内容安全状态 0未检测 1检测通过 2检测不通过',
    `content_security_risk_level` tinyint(4) DEFAULT NULL COMMENT '风险等级 0无风险 1低风险 2中风险 3高风险',
    `content_security_keywords` varchar(200) DEFAULT NULL COMMENT '命中的敏感关键词，逗号分隔',
    `mobile_province` varchar(20) DEFAULT NULL COMMENT '号码归属省份',
    `mobile_city` varchar(20) DEFAULT NULL COMMENT '号码归属城市',
    `mobile_operator` varchar(20) DEFAULT NULL COMMENT '运营商 1移动 2联通 3电信 4其他',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除 0未删除 1已删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_serial_no` (`serial_no`),
    KEY `idx_mobile` (`mobile`),
    KEY `idx_sms_type` (`sms_type`),
    KEY `idx_channel_code` (`channel_code`),
    KEY `idx_status` (`status`),
    KEY `idx_receipt_status` (`receipt_status`),
    KEY `idx_receipt_expire_time` (`receipt_expire_time`),
    KEY `idx_mobile_province` (`mobile_province`),
    KEY `idx_content_security_status` (`content_security_status`),
    KEY `idx_create_time` (`create_time`),
    KEY `idx_send_time` (`send_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短信发送记录表';

DROP TABLE IF EXISTS `sms_blacklist`;
CREATE TABLE `sms_blacklist` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `mobile` varchar(20) NOT NULL COMMENT '手机号或前缀',
    `sms_type` tinyint(4) DEFAULT NULL COMMENT '限制的短信类型，NULL表示所有类型',
    `is_prefix_match` tinyint(4) NOT NULL DEFAULT 0 COMMENT '是否前缀匹配 0否 1是',
    `reason` varchar(200) DEFAULT NULL COMMENT '拉黑原因',
    `expire_time` datetime DEFAULT NULL COMMENT '过期时间，NULL表示永久',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除 0未删除 1已删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_mobile_type_prefix` (`mobile`, `sms_type`, `is_prefix_match`, `deleted`),
    KEY `idx_is_prefix_match` (`is_prefix_match`),
    KEY `idx_expire_time` (`expire_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短信黑名单表';

DROP TABLE IF EXISTS `sms_send_time_policy`;
CREATE TABLE `sms_send_time_policy` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `policy_name` varchar(50) NOT NULL COMMENT '策略名称',
    `sms_type` tinyint(4) DEFAULT NULL COMMENT '短信类型，NULL表示所有类型',
    `time_start` varchar(10) NOT NULL COMMENT '允许开始时间，格式HH:mm',
    `time_end` varchar(10) NOT NULL COMMENT '允许结束时间，格式HH:mm',
    `weekdays` varchar(20) DEFAULT '1,2,3,4,5,6,7' COMMENT '允许的星期，1-7，逗号分隔',
    `timezone` varchar(20) DEFAULT 'Asia/Shanghai' COMMENT '时区',
    `status` tinyint(4) NOT NULL DEFAULT 1 COMMENT '状态 0禁用 1启用',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除 0未删除 1已删除',
    PRIMARY KEY (`id`),
    KEY `idx_sms_type` (`sms_type`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短信发送时段策略表';

DROP TABLE IF EXISTS `sms_mobile_location`;
CREATE TABLE `sms_mobile_location` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `mobile_prefix` varchar(7) NOT NULL COMMENT '手机号前7位',
    `province` varchar(20) NOT NULL COMMENT '省份',
    `city` varchar(20) NOT NULL COMMENT '城市',
    `operator` tinyint(4) NOT NULL COMMENT '运营商 1移动 2联通 3电信 4其他',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除 0未删除 1已删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_mobile_prefix` (`mobile_prefix`),
    KEY `idx_province` (`province`),
    KEY `idx_operator` (`operator`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='手机号归属地表';

DROP TABLE IF EXISTS `sms_sensitive_keyword`;
CREATE TABLE `sms_sensitive_keyword` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `keyword` varchar(50) NOT NULL COMMENT '敏感词',
    `category` tinyint(4) NOT NULL COMMENT '分类 1涉黄 2涉政 3涉赌 4诈骗 5其他',
    `risk_level` tinyint(4) NOT NULL DEFAULT 2 COMMENT '风险等级 1低 2中 3高',
    `status` tinyint(4) NOT NULL DEFAULT 1 COMMENT '状态 0禁用 1启用',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '逻辑删除 0未删除 1已删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_keyword` (`keyword`),
    KEY `idx_category` (`category`),
    KEY `idx_risk_level` (`risk_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='敏感词表';

INSERT INTO `sms_channel_config` (`channel_code`, `channel_name`, `is_master`, `weight`, `max_send_per_second`, `max_send_per_minute`, `max_send_per_hour`, `token_bucket_capacity`, `token_bucket_rate`, `receipt_timeout_seconds`, `max_receipt_timeout_count`, `status`) VALUES
(1, '阿里云短信', 1, 100, 100, 5000, 30000, 1000, 100, 300, 5, 1),
(2, '腾讯云短信', 0, 80, 100, 5000, 30000, 1000, 100, 300, 5, 1);

INSERT INTO `sms_send_time_policy` (`policy_name`, `sms_type`, `time_start`, `time_end`, `weekdays`, `status`) VALUES
('营销短信白天时段', 3, '09:00', '21:00', '1,2,3,4,5,6,7', 1),
('通知短信全天', 2, '00:00', '23:59', '1,2,3,4,5,6,7', 1),
('验证码短信全天', 1, '00:00', '23:59', '1,2,3,4,5,6,7', 1);

INSERT INTO `sms_sensitive_keyword` (`keyword`, `category`, `risk_level`, `status`) VALUES
('色情', 1, 3, 1),
('黄色', 1, 3, 1),
('赌博', 3, 3, 1),
('博彩', 3, 3, 1),
('中奖', 4, 2, 1),
('退款', 4, 2, 1),
('法轮功', 2, 3, 1),
('反党', 2, 3, 1),
('反动', 2, 3, 1),
('兼职', 4, 2, 1),
('刷单', 4, 3, 1),
('贷款', 4, 2, 1);

INSERT INTO `sms_mobile_location` (`mobile_prefix`, `province`, `city`, `operator`) VALUES
('1380013', '北京', '北京', 1),
('1390013', '北京', '北京', 1),
('1380010', '北京', '北京', 1),
('1390010', '北京', '北京', 1),
('1391600', '上海', '上海', 1),
('1381600', '上海', '上海', 1),
('1390220', '广东', '广州', 1),
('1380220', '广东', '深圳', 1),
('1390250', '广东', '广州', 1),
('1380251', '广东', '深圳', 1),
('1300010', '北京', '北京', 2),
('1310010', '北京', '北京', 2),
('1320010', '北京', '北京', 2),
('1560100', '北京', '北京', 2),
('1300200', '上海', '上海', 2),
('1310200', '上海', '上海', 2),
('1330010', '北京', '北京', 3),
('1330200', '上海', '上海', 3),
('1330220', '广东', '广州', 3),
('1890220', '广东', '深圳', 3);

INSERT INTO `sms_signature` (`signature_name`, `signature_content`, `sms_type`, `channel_code`, `status`) VALUES
('阿里云验证码签名', '【阿里云】', 1, 1, 1),
('阿里云通知签名', '【阿里云】', 2, 1, 1),
('阿里云营销签名', '【阿里云】', 3, 1, 1),
('腾讯云验证码签名', '【腾讯云】', 1, 2, 1),
('腾讯云通知签名', '【腾讯云】', 2, 2, 1),
('腾讯云营销签名', '【腾讯云】', 3, 2, 1);

INSERT INTO `sms_template` (`template_code`, `template_name`, `template_content`, `sms_type`, `channel_code`, `external_template_id`, `variable_names`, `status`) VALUES
('VERIFY_CODE', '验证码模板', '您的验证码是${code}，${expire}分钟内有效。', 1, 1, 'aliyun_verify_001', 'code,expire', 1),
('VERIFY_CODE', '验证码模板', '您的验证码是${code}，${expire}分钟内有效。', 1, 2, 'tencent_verify_001', 'code,expire', 1),
('ORDER_NOTIFY', '订单通知模板', '您好，您的订单${orderNo}已${status}，感谢您的支持！', 2, 1, 'aliyun_notify_001', 'orderNo,status', 1),
('ORDER_NOTIFY', '订单通知模板', '您好，您的订单${orderNo}已${status}，感谢您的支持！', 2, 2, 'tencent_notify_001', 'orderNo,status', 1),
('PROMOTION', '营销模板', '尊敬的用户，${activity}活动正在进行中，点击查看详情！', 3, 1, 'aliyun_marketing_001', 'activity', 1),
('PROMOTION', '营销模板', '尊敬的用户，${activity}活动正在进行中，点击查看详情！', 3, 2, 'tencent_marketing_001', 'activity', 1);
