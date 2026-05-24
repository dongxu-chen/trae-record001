CREATE DATABASE IF NOT EXISTS wolfkill DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE wolfkill;

CREATE TABLE IF NOT EXISTS player (
    id BIGINT NOT NULL AUTO_INCREMENT,
    nickname VARCHAR(64) NOT NULL UNIQUE,
    avatar VARCHAR(128),
    session_id VARCHAR(64),
    is_online BOOLEAN DEFAULT FALSE,
    last_heartbeat DATETIME,
    current_room_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_nickname (nickname),
    INDEX idx_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS game_room (
    id BIGINT NOT NULL,
    room_name VARCHAR(128) NOT NULL,
    max_players INT NOT NULL,
    current_players INT NOT NULL DEFAULT 0,
    password VARCHAR(64),
    host_id BIGINT NOT NULL,
    game_phase INT DEFAULT 0,
    day_number INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_host_id (host_id),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS game_record (
    id BIGINT NOT NULL AUTO_INCREMENT,
    room_id BIGINT NOT NULL,
    room_name VARCHAR(128),
    start_time DATETIME,
    end_time DATETIME,
    total_days INT DEFAULT 0,
    game_result INT DEFAULT 0,
    player_count INT DEFAULT 0,
    frames_data LONGTEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_room_id (room_id),
    INDEX idx_created_at (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS game_frame (
    id BIGINT NOT NULL AUTO_INCREMENT,
    record_id BIGINT NOT NULL,
    frame_index INT NOT NULL,
    timestamp BIGINT NOT NULL,
    day_number INT,
    game_phase INT,
    event_type VARCHAR(64),
    event_data TEXT,
    player_states LONGTEXT,
    PRIMARY KEY (id),
    INDEX idx_record_id (record_id),
    INDEX idx_frame_index (frame_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS player_stats (
    id BIGINT NOT NULL AUTO_INCREMENT,
    player_id BIGINT NOT NULL UNIQUE,
    season_id VARCHAR(64),
    elo INT NOT NULL DEFAULT 1200,
    rank_level INT DEFAULT 0,
    rank_name VARCHAR(32) DEFAULT '青铜',
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    win_streak INT DEFAULT 0,
    max_win_streak INT DEFAULT 0,
    total_games INT DEFAULT 0,
    wolf_wins INT DEFAULT 0,
    wolf_games INT DEFAULT 0,
    villager_wins INT DEFAULT 0,
    villager_games INT DEFAULT 0,
    seer_wins INT DEFAULT 0,
    seer_games INT DEFAULT 0,
    witch_wins INT DEFAULT 0,
    witch_games INT DEFAULT 0,
    hunter_wins INT DEFAULT 0,
    hunter_games INT DEFAULT 0,
    guard_wins INT DEFAULT 0,
    guard_games INT DEFAULT 0,
    total_kills INT DEFAULT 0,
    total_saves INT DEFAULT 0,
    total_checks INT DEFAULT 0,
    correct_checks INT DEFAULT 0,
    correct_votes INT DEFAULT 0,
    total_votes INT DEFAULT 0,
    play_time_seconds BIGINT DEFAULT 0,
    last_game_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_player_id (player_id),
    INDEX idx_season_id (season_id),
    INDEX idx_elo (elo DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rank_season (
    id BIGINT NOT NULL AUTO_INCREMENT,
    season_id VARCHAR(64) NOT NULL UNIQUE,
    season_name VARCHAR(64) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    total_players INT DEFAULT 0,
    total_games INT DEFAULT 0,
    base_elo INT DEFAULT 1200,
    k_factor INT DEFAULT 32,
    rank_thresholds TEXT,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_season_id (season_id),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rank_match (
    id BIGINT NOT NULL AUTO_INCREMENT,
    match_id BIGINT NOT NULL UNIQUE,
    season_id VARCHAR(64),
    game_mode VARCHAR(32),
    room_id BIGINT,
    status VARCHAR(32),
    team1_players TEXT,
    team2_players TEXT,
    team1_avg_elo INT,
    team2_avg_elo INT,
    winner_team INT,
    start_time DATETIME,
    end_time DATETIME,
    duration_seconds INT,
    total_days INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_match_id (match_id),
    INDEX idx_season_id (season_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS voice_room (
    id BIGINT NOT NULL AUTO_INCREMENT,
    room_id BIGINT NOT NULL,
    voice_room_id VARCHAR(64) UNIQUE,
    room_type VARCHAR(32),
    room_token VARCHAR(128),
    voice_server VARCHAR(128),
    voice_port INT,
    is_active BOOLEAN DEFAULT TRUE,
    max_users INT DEFAULT 12,
    current_users INT DEFAULT 0,
    allowed_user_ids TEXT,
    expire_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_room_id (room_id),
    INDEX idx_voice_room_id (voice_room_id),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
