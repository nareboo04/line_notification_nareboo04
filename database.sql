CREATE DATABASE IF NOT EXISTS `users_db`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE `users_db`;

CREATE TABLE IF NOT EXISTS `users` (
  `id`         INT AUTO_INCREMENT PRIMARY KEY,
  `user_id`    VARCHAR(255) NOT NULL UNIQUE,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `gold_history` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `bar_buy`      DECIMAL(10,2),
  `bar_sell`     DECIMAL(10,2),
  `ornament_buy`  DECIMAL(10,2),
  `ornament_sell` DECIMAL(10,2),
  `change_amount` VARCHAR(20),
  `change_status` VARCHAR(10),
  `recorded_at`  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `alerts` (
  `id`             INT AUTO_INCREMENT PRIMARY KEY,
  `user_id`        VARCHAR(255) NOT NULL,
  `asset_type`     ENUM('gold','stock','crypto') NOT NULL,
  `asset_symbol`   VARCHAR(20) DEFAULT NULL,
  `asset_market`   VARCHAR(5) NOT NULL DEFAULT 'TH',
  `target_price`   DECIMAL(20,2) NOT NULL,
  `condition_type` ENUM('above','below') NOT NULL,
  `is_active`      TINYINT(1) NOT NULL DEFAULT 1,
  `created_at`     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_user_active`  (`user_id`, `is_active`),
  INDEX `idx_asset_active` (`asset_type`, `asset_symbol`, `is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `scheduled_alerts` (
  `id`              INT AUTO_INCREMENT PRIMARY KEY,
  `user_id`         VARCHAR(255) NOT NULL,
  `asset_type`      ENUM('gold','stock','crypto') NOT NULL,
  `asset_symbol`    VARCHAR(20) DEFAULT NULL,
  `asset_market`    VARCHAR(5) NOT NULL DEFAULT 'TH',
  `schedule_time`   TIME NOT NULL,
  `schedule_days`   VARCHAR(20) NOT NULL DEFAULT 'daily',
  `is_active`       TINYINT(1) NOT NULL DEFAULT 1,
  `last_fired_date` DATE DEFAULT NULL,
  `created_at`      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_active` (`is_active`, `schedule_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
