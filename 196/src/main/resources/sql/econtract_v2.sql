-- 版本2升级脚本：添加超时催办和批量存证功能

USE econtract;

-- 1. 为合同签署人表添加超时和催办相关字段
ALTER TABLE `contract_signer`
ADD COLUMN `sign_deadline` datetime DEFAULT NULL COMMENT '签署截止时间',
ADD COLUMN `remind_count` int(11) NOT NULL DEFAULT 0 COMMENT '催办次数',
ADD COLUMN `last_remind_time` datetime DEFAULT NULL COMMENT '最后催办时间',
ADD COLUMN `pressure_data` text COMMENT '手写签名压力数据JSON',
ADD COLUMN `is_timeout` tinyint(4) NOT NULL DEFAULT 0 COMMENT '是否超时 0否 1是';

-- 2. 为存证表添加批次相关字段
ALTER TABLE `blockchain_evidence`
ADD COLUMN `batch_no` varchar(64) DEFAULT NULL COMMENT '批次号',
ADD INDEX `idx_batch_no` (`batch_no`),
ADD INDEX `idx_status` (`status`);

-- 3. 创建区块链存证批次表
DROP TABLE IF EXISTS `blockchain_batch`;
CREATE TABLE `blockchain_batch` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `batch_no` varchar(64) NOT NULL COMMENT '批次号',
  `evidence_count` int(11) NOT NULL DEFAULT 0 COMMENT '存证数量',
  `total_gas` bigint(20) DEFAULT NULL COMMENT '总Gas消耗',
  `avg_gas` bigint(20) DEFAULT NULL COMMENT '平均Gas消耗',
  `merkle_root` varchar(255) DEFAULT NULL COMMENT '默克尔根',
  `tx_id` varchar(255) DEFAULT NULL COMMENT '交易ID',
  `block_height` bigint(20) DEFAULT NULL COMMENT '区块高度',
  `block_hash` varchar(255) DEFAULT NULL COMMENT '区块哈希',
  `block_time` datetime DEFAULT NULL COMMENT '区块时间',
  `status` varchar(32) NOT NULL DEFAULT 'PENDING' COMMENT '状态 PENDING待打包 PROCESSING处理中 SUCCESS成功 FAILED失败',
  `error_msg` varchar(512) DEFAULT NULL COMMENT '错误信息',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_batch_no` (`batch_no`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='区块链存证批次表';

-- 4. 添加配置参数到应用配置（可选，也可以在代码中配置）
-- 签署超时时间：默认24小时
-- 催办间隔：默认6小时
-- 最大催办次数：默认3次
-- 批量打包数量：默认10条
-- 批量打包间隔：默认5分钟
