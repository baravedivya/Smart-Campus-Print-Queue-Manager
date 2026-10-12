-- SmartPrint: Campus Printing & Queue Management System Schema
-- Compatible with MySQL 5.7+ / MariaDB 10.3+

CREATE DATABASE IF NOT EXISTS smartprint_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smartprint_db;

-- 1. Users Table (Students & Administrators/Operators)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    roll_number VARCHAR(50) NOT NULL UNIQUE,
    phone VARCHAR(20) NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'admin') NOT NULL DEFAULT 'student',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_role (role),
    INDEX idx_user_roll (roll_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Print Orders Table
CREATE TABLE IF NOT EXISTS print_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    total_doc_pages INT NOT NULL DEFAULT 1,
    page_selection_type VARCHAR(20) NOT NULL DEFAULT 'all',
    page_range_text VARCHAR(100) DEFAULT 'All',
    selected_pages_count INT NOT NULL DEFAULT 1,
    copies INT NOT NULL DEFAULT 1,
    print_type VARCHAR(20) NOT NULL DEFAULT 'bw',        -- 'bw' or 'color'
    print_sides VARCHAR(20) NOT NULL DEFAULT 'single',   -- 'single' or 'duplex'
    paper_size VARCHAR(20) NOT NULL DEFAULT 'A4',        -- 'A4', 'A3', 'Letter'
    orientation VARCHAR(20) NOT NULL DEFAULT 'portrait', -- 'portrait' or 'landscape'
    total_printed_pages INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL DEFAULT 2.00,
    total_price DECIMAL(10, 2) NOT NULL DEFAULT 2.00,
    payment_method VARCHAR(50) NOT NULL DEFAULT 'demo_upi',
    payment_status VARCHAR(50) NOT NULL DEFAULT 'paid',   -- 'paid', 'pay_on_counter', 'pending'
    payment_ref VARCHAR(100) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',        -- 'queued', 'processing', 'ready', 'completed', 'cancelled'
    queue_position INT DEFAULT 0,
    estimated_wait_mins INT DEFAULT 5,
    pickup_token VARCHAR(20) NOT NULL UNIQUE,
    special_instructions TEXT NULL,
    printer_mode VARCHAR(50) DEFAULT 'simulation',       -- 'simulation', 'cups', 'windows_spooler'
    printer_job_id VARCHAR(100) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_order_status (status),
    INDEX idx_order_number (order_number),
    INDEX idx_pickup_token (pickup_token),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. System Settings Table (Dynamic pricing, queue configuration)
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description VARCHAR(255) NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
