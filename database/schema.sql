-- ===================================================
-- RefLens.io Database Schema (MySQL 8.x)
-- Charset: utf8mb4, Collation: utf8mb4_unicode_ci
-- ===================================================

CREATE DATABASE IF NOT EXISTS `reflens_db`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `reflens_db`;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS `users` (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `email` VARCHAR(255) NOT NULL UNIQUE,
  `username` VARCHAR(100) NOT NULL,
  `hashed_password` VARCHAR(255) NULL,
  `avatar_url` VARCHAR(500) NULL,
  `instagram_user_id` VARCHAR(100) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Boards Table (Infinite Canvas Workspace)
CREATE TABLE IF NOT EXISTS `boards` (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `user_id` VARCHAR(36) NOT NULL,
  `title` VARCHAR(255) NOT NULL DEFAULT 'Untitled Board',
  `description` TEXT NULL,
  `thumbnail_url` VARCHAR(500) NULL,
  `viewport_x` FLOAT NOT NULL DEFAULT 0.0,
  `viewport_y` FLOAT NOT NULL DEFAULT 0.0,
  `viewport_zoom` FLOAT NOT NULL DEFAULT 1.0,
  `background_theme` VARCHAR(50) NOT NULL DEFAULT 'dark-grid',
  `is_public` BOOLEAN NOT NULL DEFAULT FALSE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_boards_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  INDEX `idx_boards_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Media Items Table (Uploaded, Imported from Instagram, or external URL)
CREATE TABLE IF NOT EXISTS `media_items` (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `user_id` VARCHAR(36) NOT NULL,
  `board_id` VARCHAR(36) NOT NULL,
  `source_type` ENUM('local_upload', 'instagram', 'pixiv', 'web_bookmark', 'external_url') NOT NULL DEFAULT 'local_upload',
  `original_file_name` VARCHAR(255) NULL,
  `file_path` VARCHAR(500) NOT NULL,
  `thumbnail_path` VARCHAR(500) NULL,
  `source_url` TEXT NULL,
  `instagram_media_id` VARCHAR(100) NULL,
  `pixiv_illust_id` VARCHAR(100) NULL,
  `pixiv_page_index` INT NULL,
  `mime_type` VARCHAR(100) NOT NULL DEFAULT 'image/jpeg',
  `file_size` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `width` INT UNSIGNED NOT NULL DEFAULT 0,
  `height` INT UNSIGNED NOT NULL DEFAULT 0,
  `aspect_ratio` FLOAT NOT NULL DEFAULT 1.0,
  `folder_name` VARCHAR(100) NOT NULL DEFAULT 'Unsorted',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_media_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_media_board` FOREIGN KEY (`board_id`) REFERENCES `boards` (`id`) ON DELETE CASCADE,
  INDEX `idx_media_board_id` (`board_id`),
  INDEX `idx_media_user_id` (`user_id`),
  INDEX `idx_media_pixiv_illust_id` (`pixiv_illust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Canvas Items Table (PureRef-style transformed placements on infinite canvas)
CREATE TABLE IF NOT EXISTS `canvas_items` (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `board_id` VARCHAR(36) NOT NULL,
  `media_item_id` VARCHAR(36) NOT NULL,
  `pos_x` FLOAT NOT NULL DEFAULT 0.0,
  `pos_y` FLOAT NOT NULL DEFAULT 0.0,
  `width` FLOAT NOT NULL DEFAULT 300.0,
  `height` FLOAT NOT NULL DEFAULT 300.0,
  `rotation` FLOAT NOT NULL DEFAULT 0.0,
  `z_index` INT NOT NULL DEFAULT 1,
  `is_flipped_h` BOOLEAN NOT NULL DEFAULT FALSE,
  `is_flipped_v` BOOLEAN NOT NULL DEFAULT FALSE,
  `is_grayscale` BOOLEAN NOT NULL DEFAULT FALSE,
  `opacity` FLOAT NOT NULL DEFAULT 1.0,
  `border_color` VARCHAR(30) NOT NULL DEFAULT 'transparent',
  `border_width` INT NOT NULL DEFAULT 0,
  `is_locked` BOOLEAN NOT NULL DEFAULT FALSE,
  `caption` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_canvas_board` FOREIGN KEY (`board_id`) REFERENCES `boards` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_canvas_media` FOREIGN KEY (`media_item_id`) REFERENCES `media_items` (`id`) ON DELETE CASCADE,
  INDEX `idx_canvas_board_id` (`board_id`),
  INDEX `idx_canvas_media_id` (`media_item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. AI Analyses Table (Gemini Vision Multimodal Inspection)
CREATE TABLE IF NOT EXISTS `ai_analyses` (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `media_item_id` VARCHAR(36) NOT NULL UNIQUE,
  `composition` TEXT NOT NULL,
  `lighting` TEXT NOT NULL,
  `pose_anatomy` TEXT NOT NULL,
  `costume_structure` TEXT NOT NULL,
  `palette_json` JSON NOT NULL,
  `tags_json` JSON NOT NULL,
  `raw_prompt` TEXT NULL,
  `raw_response` JSON NULL,
  `analysis_model` VARCHAR(100) NOT NULL DEFAULT 'gemini-1.5-flash',
  `analyzed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_ai_media` FOREIGN KEY (`media_item_id`) REFERENCES `media_items` (`id`) ON DELETE CASCADE,
  INDEX `idx_ai_media_id` (`media_item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Instagram Integrations Table (OAuth token storage)
CREATE TABLE IF NOT EXISTS `instagram_accounts` (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `user_id` VARCHAR(36) NOT NULL UNIQUE,
  `instagram_user_id` VARCHAR(100) NOT NULL,
  `instagram_username` VARCHAR(100) NOT NULL,
  `access_token` TEXT NOT NULL,
  `token_type` VARCHAR(50) NOT NULL DEFAULT 'bearer',
  `expires_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_ig_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Pixiv Integrations Table (公式 App API の OAuth token storage)
CREATE TABLE IF NOT EXISTS `pixiv_accounts` (
  `id` VARCHAR(36) NOT NULL PRIMARY KEY,
  `user_id` VARCHAR(36) NOT NULL,
  `pixiv_user_id` VARCHAR(100) NOT NULL,
  `pixiv_username` VARCHAR(100) NOT NULL,
  `pixiv_account` VARCHAR(100) NULL,
  `access_token` TEXT NOT NULL,
  `refresh_token` TEXT NULL,
  `expires_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_pixiv_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
