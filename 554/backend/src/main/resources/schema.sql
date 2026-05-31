CREATE DATABASE IF NOT EXISTS checkin_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE checkin_system;

INSERT INTO user (username, password, nickname, points, recheck_cards, create_time, update_time) 
VALUES ('test', '123456', '测试用户', 0, 3, NOW(), NOW())
ON DUPLICATE KEY UPDATE username = username;
