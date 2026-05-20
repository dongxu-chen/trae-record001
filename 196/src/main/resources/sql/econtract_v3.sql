-- 版本3升级脚本：添加合同智能审查、意愿认证、验真功能

USE econtract;

-- 1. 合同审查表
DROP TABLE IF EXISTS `contract_review`;
CREATE TABLE `contract_review` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `contract_id` bigint(20) NOT NULL COMMENT '合同ID',
  `review_result` text COMMENT '审查结果JSON',
  `missing_clauses` text COMMENT '缺失条款列表JSON',
  `risk_clauses` text COMMENT '风险条款列表JSON',
  `risk_level` varchar(32) DEFAULT 'LOW' COMMENT '风险等级 LOW低 MEDIUM中 HIGH高',
  `total_score` int(11) DEFAULT 100 COMMENT '综合评分(0-100)',
  `reviewer_id` bigint(20) DEFAULT NULL COMMENT '审查人ID',
  `review_time` datetime DEFAULT NULL COMMENT '审查时间',
  `status` varchar(32) NOT NULL DEFAULT 'PENDING' COMMENT '状态 PENDING待审查 REVIEWED已审查',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_contract_id` (`contract_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同审查表';

-- 2. 意愿认证表
DROP TABLE IF EXISTS `witness_auth`;
CREATE TABLE `witness_auth` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `contract_id` bigint(20) NOT NULL COMMENT '合同ID',
  `signer_id` bigint(20) NOT NULL COMMENT '签署人ID',
  `auth_type` varchar(32) NOT NULL DEFAULT 'VIDEO' COMMENT '认证类型 VIDEO视频 AUDIO音频',
  `video_path` varchar(255) DEFAULT NULL COMMENT '视频文件路径',
  `video_duration` int(11) DEFAULT NULL COMMENT '视频时长(秒)',
  `video_size` bigint(20) DEFAULT NULL COMMENT '视频大小(字节)',
  `video_hash` varchar(128) DEFAULT NULL COMMENT '视频哈希',
  `face_detected` tinyint(4) DEFAULT 0 COMMENT '是否检测到人脸',
  `face_similarity` decimal(10,4) DEFAULT NULL COMMENT '人脸相似度',
  `liveness_passed` tinyint(4) DEFAULT 0 COMMENT '是否通过活体验证',
  `speech_text` text COMMENT '语音转文字内容',
  `auth_result` varchar(32) DEFAULT 'PENDING' COMMENT '认证结果 PENDING PASS FAIL',
  `auth_time` datetime DEFAULT NULL COMMENT '认证时间',
  `tx_id` varchar(255) DEFAULT NULL COMMENT '区块链交易ID',
  `blockchain_time` datetime DEFAULT NULL COMMENT '上链时间',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_contract_id` (`contract_id`),
  KEY `idx_signer_id` (`signer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意愿认证表';

-- 3. 合同验真日志表
DROP TABLE IF EXISTS `contract_verify_log`;
CREATE TABLE `contract_verify_log` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `contract_no` varchar(64) NOT NULL COMMENT '合同编号',
  `verify_type` varchar(32) NOT NULL DEFAULT 'PUBLIC' COMMENT '验证类型 PUBLIC公开 INTERNAL内部',
  `requester_ip` varchar(64) DEFAULT NULL COMMENT '请求IP',
  `requester_info` varchar(512) DEFAULT NULL COMMENT '请求者信息',
  `verify_result` varchar(32) NOT NULL COMMENT '验证结果',
  `verify_detail` text COMMENT '验证详情JSON',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_contract_no` (`contract_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同验真日志表';

-- 4. 为合同表添加审查相关字段
ALTER TABLE `contract`
ADD COLUMN `review_status` varchar(32) DEFAULT 'PENDING' COMMENT '审查状态 PENDING待审查 REVIEWED已审查',
ADD COLUMN `risk_level` varchar(32) DEFAULT 'LOW' COMMENT '风险等级',
ADD COLUMN `review_score` int(11) DEFAULT 100 COMMENT '审查评分',
ADD COLUMN `allow_public_verify` tinyint(4) NOT NULL DEFAULT 1 COMMENT '是否允许公开验真 0否 1是',
ADD INDEX `idx_review_status` (`review_status`);

-- 5. 为签署人表添加意愿认证ID
ALTER TABLE `contract_signer`
ADD COLUMN `witness_auth_id` bigint(20) DEFAULT NULL COMMENT '意愿认证ID',
ADD INDEX `idx_witness_auth_id` (`witness_auth_id`);

-- 6. 插入审查规则配置（可选，存入application.yml或配置表）
-- 缺失条款规则：当事人信息、标的、数量、质量、价款、履行期限、违约责任、争议解决
-- 风险条款规则：不可抗力、免责条款、单方解除权、违约金过高、管辖约定
