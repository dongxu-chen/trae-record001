CREATE DATABASE IF NOT EXISTS econtract DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE econtract;

DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` varchar(64) NOT NULL COMMENT '用户名',
  `password` varchar(128) NOT NULL COMMENT '密码',
  `real_name` varchar(64) NOT NULL COMMENT '真实姓名',
  `phone` varchar(20) NOT NULL COMMENT '手机号',
  `id_card` varchar(32) DEFAULT NULL COMMENT '身份证号',
  `email` varchar(64) DEFAULT NULL COMMENT '邮箱',
  `face_image` varchar(255) DEFAULT NULL COMMENT '人脸照片',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态 0禁用 1启用',
  `identity_verified` tinyint(4) NOT NULL DEFAULT '0' COMMENT '实名认证 0未认证 1已认证',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标记',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

DROP TABLE IF EXISTS `contract_template`;
CREATE TABLE `contract_template` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `template_name` varchar(128) NOT NULL COMMENT '模板名称',
  `template_type` varchar(64) NOT NULL COMMENT '模板类型',
  `template_code` varchar(64) NOT NULL COMMENT '模板编码',
  `file_path` varchar(255) NOT NULL COMMENT '文件路径',
  `file_name` varchar(255) NOT NULL COMMENT '文件名称',
  `file_size` bigint(20) DEFAULT NULL COMMENT '文件大小',
  `fields` text COMMENT '模板字段配置JSON',
  `sign_positions` text COMMENT '签名位置配置JSON',
  `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态 0禁用 1启用',
  `creator_id` bigint(20) NOT NULL COMMENT '创建人ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标记',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_code` (`template_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同模板表';

DROP TABLE IF EXISTS `contract`;
CREATE TABLE `contract` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `contract_no` varchar(64) NOT NULL COMMENT '合同编号',
  `contract_name` varchar(255) NOT NULL COMMENT '合同名称',
  `template_id` bigint(20) DEFAULT NULL COMMENT '模板ID',
  `file_path` varchar(255) NOT NULL COMMENT '文件路径',
  `file_name` varchar(255) NOT NULL COMMENT '文件名称',
  `file_hash` varchar(128) DEFAULT NULL COMMENT '文件哈希',
  `form_data` text COMMENT '表单数据JSON',
  `status` varchar(32) NOT NULL DEFAULT 'DRAFT' COMMENT '状态 DRAFT草稿 PENDING待签署 SIGNING签署中 COMPLETED已完成 REJECTED已拒签 EXPIRED已过期',
  `creator_id` bigint(20) NOT NULL COMMENT '创建人ID',
  `expire_time` datetime DEFAULT NULL COMMENT '过期时间',
  `blockchain_hash` varchar(255) DEFAULT NULL COMMENT '区块链存证哈希',
  `blockchain_tx_id` varchar(255) DEFAULT NULL COMMENT '区块链交易ID',
  `blockchain_time` datetime DEFAULT NULL COMMENT '区块链存证时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标记',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_contract_no` (`contract_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同表';

DROP TABLE IF EXISTS `contract_signer`;
CREATE TABLE `contract_signer` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `contract_id` bigint(20) NOT NULL COMMENT '合同ID',
  `signer_id` bigint(20) NOT NULL COMMENT '签署人ID',
  `signer_name` varchar(64) NOT NULL COMMENT '签署人姓名',
  `signer_phone` varchar(20) NOT NULL COMMENT '签署人手机号',
  `sign_order` int(11) NOT NULL COMMENT '签署顺序',
  `sign_status` varchar(32) NOT NULL DEFAULT 'PENDING' COMMENT '签署状态 PENDING待签署 SIGNING签署中 COMPLETED已签署 REJECTED已拒签',
  `sign_time` datetime DEFAULT NULL COMMENT '签署时间',
  `signature_image` varchar(255) DEFAULT NULL COMMENT '签名图片路径',
  `signature_type` varchar(32) DEFAULT NULL COMMENT '签名类型 HANDWRITE手写 DRAG拖动',
  `sign_position` text COMMENT '签名位置JSON',
  `sign_ip` varchar(64) DEFAULT NULL COMMENT '签署IP',
  `sign_device` varchar(255) DEFAULT NULL COMMENT '签署设备',
  `auth_type` varchar(32) DEFAULT NULL COMMENT '认证类型 SMS短信 FACE人脸',
  `auth_time` datetime DEFAULT NULL COMMENT '认证时间',
  `timestamp_token` varchar(255) DEFAULT NULL COMMENT '时间戳令牌',
  `sign_note` varchar(512) DEFAULT NULL COMMENT '签署备注',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` tinyint(4) NOT NULL DEFAULT '0' COMMENT '删除标记',
  PRIMARY KEY (`id`),
  KEY `idx_contract_id` (`contract_id`),
  KEY `idx_signer_id` (`signer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同签署人表';

DROP TABLE IF EXISTS `sign_log`;
CREATE TABLE `sign_log` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `contract_id` bigint(20) NOT NULL COMMENT '合同ID',
  `signer_id` bigint(20) NOT NULL COMMENT '签署人ID',
  `operation` varchar(64) NOT NULL COMMENT '操作类型',
  `detail` text COMMENT '操作详情',
  `ip_address` varchar(64) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` varchar(512) DEFAULT NULL COMMENT '用户代理',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_contract_id` (`contract_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='签署日志表';

DROP TABLE IF EXISTS `sms_code`;
CREATE TABLE `sms_code` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `phone` varchar(20) NOT NULL COMMENT '手机号',
  `code` varchar(8) NOT NULL COMMENT '验证码',
  `biz_type` varchar(32) NOT NULL COMMENT '业务类型 LOGIN SIGN IDENTITY',
  `expire_time` datetime NOT NULL COMMENT '过期时间',
  `used` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否使用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_phone_biz` (`phone`,`biz_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短信验证码表';

DROP TABLE IF EXISTS `face_verify_log`;
CREATE TABLE `face_verify_log` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `verify_type` varchar(32) NOT NULL COMMENT '认证类型 LOGIN SIGN',
  `face_image` varchar(255) DEFAULT NULL COMMENT '人脸照片',
  `similarity` decimal(10,4) DEFAULT NULL COMMENT '相似度',
  `passed` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否通过',
  `request_id` varchar(128) DEFAULT NULL COMMENT '请求ID',
  `error_msg` varchar(512) DEFAULT NULL COMMENT '错误信息',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人脸认证日志表';

DROP TABLE IF EXISTS `blockchain_evidence`;
CREATE TABLE `blockchain_evidence` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `evidence_no` varchar(64) NOT NULL COMMENT '存证编号',
  `biz_type` varchar(32) NOT NULL COMMENT '业务类型 CONTRACT SIGN',
  `biz_id` bigint(20) NOT NULL COMMENT '业务ID',
  `data_hash` varchar(128) NOT NULL COMMENT '数据哈希',
  `data_content` text COMMENT '存证数据JSON',
  `tx_id` varchar(255) DEFAULT NULL COMMENT '交易ID',
  `block_height` bigint(20) DEFAULT NULL COMMENT '区块高度',
  `block_hash` varchar(255) DEFAULT NULL COMMENT '区块哈希',
  `block_time` datetime DEFAULT NULL COMMENT '区块时间',
  `status` varchar(32) NOT NULL DEFAULT 'PENDING' COMMENT '状态 PENDING处理中 SUCCESS成功 FAILED失败',
  `error_msg` varchar(512) DEFAULT NULL COMMENT '错误信息',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_evidence_no` (`evidence_no`),
  KEY `idx_biz` (`biz_type`,`biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='区块链存证表';

INSERT INTO `sys_user` (`username`, `password`, `real_name`, `phone`, `id_card`, `status`, `identity_verified`) VALUES
('admin', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '管理员', '13800000001', '110101199001010001', 1, 1),
('user1', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '张三', '13800000002', '110101199002020002', 1, 1),
('user2', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '李四', '13800000003', '110101199003030003', 1, 1);
