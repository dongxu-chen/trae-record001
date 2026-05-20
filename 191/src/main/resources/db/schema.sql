CREATE DATABASE IF NOT EXISTS file_storage DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE file_storage;

CREATE TABLE IF NOT EXISTS tenant (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_code VARCHAR(64) NOT NULL UNIQUE COMMENT '租户编码',
    tenant_name VARCHAR(128) NOT NULL COMMENT '租户名称',
    storage_quota BIGINT DEFAULT 0 COMMENT '存储配额(字节)',
    used_storage BIGINT DEFAULT 0 COMMENT '已使用存储(字节)',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-启用, 0-禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_code (tenant_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='租户表';

CREATE TABLE IF NOT EXISTS file_info (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    file_md5 VARCHAR(32) NOT NULL COMMENT '文件MD5',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名称',
    file_path VARCHAR(512) NOT NULL COMMENT '文件存储路径',
    file_size BIGINT NOT NULL COMMENT '文件大小(字节)',
    file_type VARCHAR(64) COMMENT '文件类型(MIME)',
    file_extension VARCHAR(16) COMMENT '文件扩展名',
    upload_user VARCHAR(64) COMMENT '上传用户',
    is_deleted TINYINT DEFAULT 0 COMMENT '是否删除: 0-否, 1-是',
    has_thumbnail TINYINT DEFAULT 0 COMMENT '是否有缩略图: 0-否, 1-是',
    thumbnail_path VARCHAR(512) COMMENT '缩略图路径',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_file_md5 (file_md5),
    INDEX idx_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件信息表';

CREATE TABLE IF NOT EXISTS file_chunk (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    upload_id VARCHAR(64) NOT NULL COMMENT '上传任务ID',
    file_md5 VARCHAR(32) NOT NULL COMMENT '文件MD5',
    chunk_number INT NOT NULL COMMENT '分片序号',
    chunk_size BIGINT NOT NULL COMMENT '分片大小',
    total_chunks INT NOT NULL COMMENT '总分片数',
    total_size BIGINT NOT NULL COMMENT '文件总大小',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名称',
    upload_user VARCHAR(64) COMMENT '上传用户',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-上传中, 1-已完成, 2-已失败',
    expired_at DATETIME NOT NULL COMMENT '过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_upload_id (upload_id),
    INDEX idx_tenant_md5 (tenant_id, file_md5),
    INDEX idx_expired_at (expired_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件分片表';

CREATE TABLE IF NOT EXISTS file_share (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    file_id BIGINT NOT NULL COMMENT '文件ID',
    share_code VARCHAR(32) NOT NULL UNIQUE COMMENT '分享码',
    extract_code VARCHAR(16) COMMENT '提取码',
    share_user VARCHAR(64) COMMENT '分享用户',
    view_count INT DEFAULT 0 COMMENT '访问次数',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    expire_at DATETIME COMMENT '过期时间',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-有效, 0-无效',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_share_code (share_code),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_expire_at (expire_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件分享表';

CREATE TABLE IF NOT EXISTS recycle_bin (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    file_id BIGINT NOT NULL COMMENT '文件ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名称',
    file_size BIGINT NOT NULL COMMENT '文件大小',
    delete_user VARCHAR(64) COMMENT '删除用户',
    expire_at DATETIME NOT NULL COMMENT '过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_file_id (file_id),
    INDEX idx_expire_at (expire_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回收站表';

CREATE TABLE IF NOT EXISTS file_version (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '租户ID',
    file_id BIGINT NOT NULL COMMENT '文件ID',
    version_number INT NOT NULL COMMENT '版本号',
    file_md5 VARCHAR(32) NOT NULL COMMENT '文件MD5',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名称',
    file_path VARCHAR(512) NOT NULL COMMENT '文件存储路径',
    file_size BIGINT NOT NULL COMMENT '文件大小(字节)',
    file_type VARCHAR(64) COMMENT '文件类型(MIME)',
    file_extension VARCHAR(16) COMMENT '文件扩展名',
    upload_user VARCHAR(64) COMMENT '上传用户',
    change_description VARCHAR(500) COMMENT '变更说明',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_file_id (file_id),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_version (file_id, version_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件版本表';
